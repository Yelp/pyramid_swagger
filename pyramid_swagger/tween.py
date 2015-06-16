# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import namedtuple
from contextlib import contextmanager
import functools
import logging
import re

from pyramid.interfaces import IRoutesMapper
import jsonschema.exceptions
import simplejson

from pyramid_swagger.exceptions import RequestValidationError
from pyramid_swagger.exceptions import ResponseValidationError
from pyramid_swagger.model import PathNotMatchedError


log = logging.getLogger(__name__)


DEFAULT_EXCLUDED_PATHS = [
    r'^/static/?',
    r'^/api-docs/?'
]


class Settings(namedtuple(
    'Settings',
    [
        'schema',
        'validate_request',
        'validate_response',
        'validate_path',
        'exclude_paths',
        'exclude_routes',
    ]
)):

    """A settings object for configuratble options.

    :param schema: a :class:`pyramid_swagger.model.SwaggerSchema`
    :param validate_swagger_spec: check Swagger files for correctness.
    :param validate_request: check requests against Swagger spec.
    :param validate_response: check responses against Swagger spec.
    :param validate_path: check if request path is in schema. If disabled
        and path not found in schema, request / response validation is skipped.
    :param exclude_paths: list of paths (in regex format) that should be
        excluded from validation.
    :rtype: namedtuple
    :param exclude_routes: list of route names that should be excluded from
        validation.
    """


@contextmanager
def noop_context(request, response=None):
    yield


def _get_validation_context(registry):
    validation_context_path = registry.settings.get(
        'pyramid_swagger.validation_context_path',
    )

    if validation_context_path:
        m = re.match(
            '(?P<module_path>.*)\.(?P<contextmanager_name>.*)',
            validation_context_path,
        )
        module_path = m.group('module_path')
        contextmanager_name = m.group('contextmanager_name')

        return getattr(
            __import__(module_path, fromlist=contextmanager_name),
            contextmanager_name,
        )
    else:
        return noop_context


def validation_tween_factory(handler, registry):
    """Pyramid tween for performing validation.

    Note this is very simple -- it validates requests, responses, and paths
    while delegating to the relevant matching view.
    """
    settings = load_settings(registry)
    route_mapper = registry.queryUtility(IRoutesMapper)

    def validator_tween(request):
        # We don't have access to this yet but let's go ahead and build the
        # matchdict so we can validate it and use it to exclude routes from
        # validation.
        route_info = route_mapper(request)

        if should_exclude_request(settings, request, route_info):
            return handler(request)

        validation_context = _get_validation_context(registry)

        try:
            validator_map = settings.schema.validators_for_request(request)
        except PathNotMatchedError as exc:
            if settings.validate_path:
                with validation_context(request):
                    raise RequestValidationError(str(exc))
            else:
                return handler(request)

        if settings.validate_request:
            request_data = handle_request(
                PyramidSwaggerRequest(request, route_info),
                validation_context,
                validator_map)

            def swagger_data(_):
                return request_data

            request.set_property(swagger_data)

        response = handler(request)

        if settings.validate_response:
            with validation_context(request, response=response):
                validate_response(response, validator_map.response)

        return response

    return validator_tween


class PyramidSwaggerRequest(object):
    """Adapter for a :class:`pyramid.request.Request` which exposes request
    data for casting and validation.
    """

    FORM_TYPES = [
        'application/x-www-form-urlencoded',
        'multipart/form-data',
    ]

    def __init__(self, request, route_info):
        self.request = request
        self.route_info = route_info

    @property
    def query(self):
        return self.request.GET

    @property
    def path(self):
        return self.route_info.get('match') or {}

    @property
    def headers(self):
        return self.request.headers

    @property
    def form(self):
        # Don't read the POST dict unless the body is form encoded
        if self.request.headers.get('Content-Type') in self.FORM_TYPES:
            return self.request.POST
        return {}

    @property
    def body(self):
        return getattr(self.request, 'json_body', {})


def handle_request(request, validation_context, validator_map):
    """Validate the request against the swagger spec and return a dict with
    all parameter values available in the request, casted to the expected
    python type.

    :param request: a :class:`PyramidSwaggerRequest` to validate
    :param validation_context: a context manager for wrapping validation
        errors
    :param validator_map: a :class:`pyramid_swagger.load_schema.ValidatorMap`
        used to validate the request
    :returns: a :class:`dict` of request data for each parameter in the swagger
        spec
    """
    request_data = {}
    validation_pairs = []

    for validator, values in [
        (validator_map.query, request.query),
        (validator_map.path, request.path),
        (validator_map.form, request.form),
        (validator_map.headers, request.headers),
    ]:
        values = cast_params(validator.schema, values)
        validation_pairs.append((validator, values))
        request_data.update(values)

    # Body is a special case because the key for the request_data comes
    # from the name in the schema, instead of keys in the values
    if validator_map.body.schema:
        param_name = validator_map.body.schema['name']
        validation_pairs.append((validator_map.body, request.body))
        request_data[param_name] = request.body

    with validation_context(request):
        validate_request(validation_pairs)

    return request_data


def load_settings(registry):
    return Settings(
        schema=registry.settings['pyramid_swagger.schema'],
        validate_request=registry.settings.get(
            'pyramid_swagger.enable_request_validation',
            True
        ),
        validate_response=registry.settings.get(
            'pyramid_swagger.enable_response_validation',
            True
        ),
        validate_path=registry.settings.get(
            'pyramid_swagger.enable_path_validation',
            True
        ),
        exclude_paths=get_exclude_paths(registry),
        exclude_routes=set(registry.settings.get(
            'pyramid_swagger.exclude_routes',
        ) or []),
    )


def get_exclude_paths(registry):
    """Compiles a list of paths that should not be validated against.
        :rtype: list of compiled validation regexes
    """
    # TODO(#63): remove deprecated `skip_validation` setting in v2.0.
    regexes = registry.settings.get(
        'pyramid_swagger.skip_validation',
        registry.settings.get(
            'pyramid_swagger.exclude_paths',
            DEFAULT_EXCLUDED_PATHS
        )
    )

    # being nice to users using strings :p
    if not isinstance(regexes, list) and not isinstance(regexes, tuple):
        regexes = [regexes]

    return [re.compile(r) for r in regexes]


def should_exclude_request(settings, request, route_info):
    disable_all_validation = not any((
        settings.validate_request,
        settings.validate_response,
        settings.validate_path
    ))
    return (
        disable_all_validation or
        should_exclude_path(settings.exclude_paths, request.path) or
        should_exclude_route(settings.exclude_routes, route_info)
    )


def should_exclude_path(exclude_path_regexes, path):
    # Skip validation for the specified endpoints
    return any(r.match(path) for r in exclude_path_regexes)


def should_exclude_route(excluded_routes, route_info):
    return (
        route_info.get('route') and
        route_info['route'].name in excluded_routes
    )


def validation_error(exc_class):
    def decorator(f):
        @functools.wraps(f)
        def _validate(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except jsonschema.exceptions.ValidationError as exc:
                # This will alter our stack trace slightly, but Pyramid knows
                # how to render it. And the real value is in the message
                # anyway.
                raise exc_class(str(exc))

        return _validate

    return decorator


CAST_TYPE_TO_FUNC = {
    'integer': int,
    'float': float,
    'number': float,
    'boolean': bool,
}


def cast_request_param(param_type, param_name, param_value):
    """Try to cast a request param (e.g. query arg, POST data) from a string to
    its specified type in the schema. This allows validating non-string params.

    :param param_type: name of the type to be casted to
    :type  param_type: string
    :param param_name: param name
    :type  param_name: string
    :param param_value: param value
    :type  param_value: string
    """
    try:
        return CAST_TYPE_TO_FUNC.get(param_type, lambda x: x)(param_value)
    except ValueError:
        log.warn("Failed to cast %s value of %s to %s",
                 param_name, param_value, param_type)
        # Ignore type error, let jsonschema validation handle incorrect types
        return param_value


@validation_error(RequestValidationError)
def validate_request(validation_pairs):
    for validator, values in validation_pairs:
        validator.validate(values)


def cast_params(schema, values):
    if not schema:
        return {}

    def get_type(param_name):
        return schema['properties'].get(param_name, {}).get('type')

    return dict(
        (k, cast_request_param(get_type(k), k, v))
        for k, v in values.items()
    )


@validation_error(ResponseValidationError)
def validate_response(response, validator):
    """Validates response against our schemas.

    :param response: the response object to validate
    :type response: :class:`pyramid.response.Response`
    :param validator: validator for the response
    :type  validator: :class`:pyramid_swagger.load_schema.SchemaValidator`
    """
    # Short circuit if we are supposed to not validate anything.
    if (
        validator.schema.get('type') == 'void' and
        response.body in (None, b'', b'{}', b'null')
    ):
        return

    # Don't attempt to validate non-success responses
    if not 200 <= response.status_code <= 203:
        return

    validator.validate(prepare_body(response))


def prepare_body(response):
    # content_type and charset must both be set to access response.text
    if response.content_type is None or response.charset is None:
        raise ResponseValidationError(
            'Response validation error: Content-Type and charset must be set'
        )

    if 'application/json' in response.content_type:
        return simplejson.loads(response.text)
    else:
        return response.text
