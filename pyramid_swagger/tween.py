# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from contextlib import contextmanager
from pyramid.interfaces import IRoutesMapper

from collections import namedtuple
import functools
import re

import jsonschema.exceptions
import simplejson
from pyramid_swagger.exceptions import RequestValidationError
from pyramid_swagger.exceptions import ResponseValidationError
from .model import PathNotMatchedError


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

        handle_request(
            settings,
            PyramidSwaggerRequest(request, route_info),
            validation_context,
            # TODO: replace with validation mapping
            schema_data,
            resolver)
        response = handler(request)

        if settings.validate_response:
            with validation_context(request, response=response):
                validate_response(response, validator_map.response)

        return response

    return validator_tween


class PyramidSwaggerRequest(object):
    """Adopter for a :class:`pyramid.request.Request` which exposes request
    data for casting and validation.
    """

    def __init__(self, request, route_info):
        self.request = request
        self.route_info = route_info

    @property
    def query(self):
        return self.request.GET.items()

    @property
    def path(self):
        return (self.route_info.get('match') or {}).items()

    @property
    def headers(self):
        return self.request.headers.items()

    @property
    def body(self):
        return getattr(self.request, 'json_body', {})


def handle_request(settings, request, validation_context, schema_map, resolver):
    if not settings.validate_request:
        return

    request_data = {}
    validation_pairs = []

    for schema, values in [
        (schema_map.request_query_schema, request.query),
        (schema_map.request_path_schema, request.path),
        (schema_map.request_header_schema, request.headers),
    ]:
        values = cast_params(schema, values, DEFAULT_FORMAT_MAPPING)
        validation_pairs.append((schema, values))
        request_data.update(values)

    if schema_map.request_body_schema:
        param_name, _ = schema_map.request_body_schema
        request_data[param_name] = request.body

    with validation_context(request):
        values = validate_request(validation_pairs, request, schema_map, resolver)

    def swagger_data(_):
        return request_values

    # TODO: test cases
    request.request.set_property(swagger_data, b'swagger_data')


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
                # This will alter our stack trace slightly, but Pyramid knows how
                # to render it. And the real value is in the message anyway.
                raise exc_class(str(exc))

        return _validate

    return decorator


# TODO: cast date types
DEFAULT_FORMAT_MAPPING = {
    'integer': int,
    'float': float,
    'boolean': bool,
}


def cast_request_param(request_schema, param_name, param_value, format_mapping):
    """Try to cast a request param (e.g. query arg, POST data) from a string to
    its specified type in the schema. This allows validating non-string params.

    :param request_schema: request schema
    :type request_schema: dict
    :param param_name: param name
    :type  param_name: string
    :param param_value: param value
    :type  param_value: string
    :param format_mapping: a mapping of format name to callable which casts
        the value to the correct type.
    """
    param_type = request_schema['properties'].get(param_name, {}).get('type')
    try:
        return format_mapping.get(param_type, lambda x: x)(param_value)
    except ValueError:
        # TODO: log a warning here
        # Ignore type error, let jsonschema validation handle incorrect types
        return param_value


@validation_error(RequestValidationError)
def validate_request(request_match, request, validator_map):
    """Validates an incoming request against our schemas.

    :param route_match: a dict with all the path params and their values from
        the request
    :param route_match: dict
    :param request: the request object to validate
    :type request: Pyramid request object passed into a view
    :param validator_map: A :class:`pyramid_swagger.load_schema.ValidatorMap`
        used to validate the request.
    """
    for validator, values in [
        (validator_map.query, request.GET.items()),
        (validator_map.path, route_match),
        (validator_map.headers, request.headers.items()),
    ]:
        validator.validate(cast_params(validator.schema, values))

    if not validator_map.body.schema:
        return
    validator_map.body.validate(getattr(request, 'json_body', {}))


def cast_params(schema, values, format_mapping):
    if not schema:
        return {}
    return dict(
        (k, cast_request_param(schema, k, v, format_mapping))
        for k, v in values)


def validate_param_values(request_schema, values, resolver):
    # You'll notice we use Draft3 some places and Draft4 in others.
    # Unfortunately this is just Swagger's inconsistency showing. It
    # may be nice in the future to do the necessary munging to make
    # everything Draft4 compatible, although the Swagger UI will
    # probably never truly support Draft5.
    Draft3Validator(
        request_schema,
        resolver=resolver,
        types=EXTENDED_TYPES,
    ).validate(values)


@validation_error(ResponseValidationError)
def validate_response(response, schema_map, resolver):
    """Validates response against our schemas.

    :param response: the response object to validate
    :type response: Requests response object
    """
    # Short circuit if we are supposed to not validate anything.
    if (
        validator.schema.get('type') == 'void' and
        response.body in (None, b'', b'{}', b'null')
    ):
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
