# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools
import logging
import re
import sys
from collections import namedtuple
from contextlib import contextmanager

import bravado_core
import jsonschema.exceptions
import simplejson
from bravado_core.exception import SwaggerMappingError
from bravado_core.formatter import SwaggerFormat  # noqa
from bravado_core.request import IncomingRequest
from bravado_core.request import unmarshal_request
from bravado_core.response import get_response_spec
from bravado_core.response import OutgoingResponse
from pyramid.interfaces import IRoutesMapper
from pyramid.settings import asbool
from pyramid.settings import aslist

from pyramid_swagger.exceptions import PathNotFoundError
from pyramid_swagger.exceptions import RequestValidationError
from pyramid_swagger.exceptions import ResponseValidationError
from pyramid_swagger.model import PathNotMatchedError


log = logging.getLogger(__name__)


SWAGGER_12 = '1.2'
SWAGGER_20 = '2.0'
DEFAULT_SWAGGER_VERSIONS = [SWAGGER_20]
SUPPORTED_SWAGGER_VERSIONS = [SWAGGER_12, SWAGGER_20]


DEFAULT_EXCLUDED_PATHS = [
    r'^/static/?',
    r'^/api-docs/?',
    r'^/swagger.(json|yaml)',
]


class Settings(namedtuple(
    'Settings',
    [
        'swagger12_handler',
        'swagger20_handler',
        'validate_request',
        'validate_response',
        'validate_path',
        'exclude_paths',
        'exclude_routes',
        'prefer_20_routes',
    ]
)):

    """A settings object for configurable options.

    :param swagger12_handler: a :class:`SwaggerHandler` for v1.2 or None
    :param swagger20_handler: a :class:`SwaggerHandler` for v2.0 or None
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
    :param prefer_20_routes: list of route names that should be handled
        via v2.0 spec when `2.0` is in `swagger_versions`. All others will be
        handled via v1.2 spec. [i.e. Make v2.0 an opt-in feature]
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


def get_swagger_objects(settings, route_info, registry):
    """Returns appropriate swagger handler and swagger spec schema.

    Swagger Handler contains callables that isolate implementation differences
    in the tween to handle both Swagger 1.2 and Swagger 2.0.

    Exception is made when `settings.prefer_20_routes` are non-empty and
    ['1.2', '2.0'] both are present in available swagger versions. In this
    special scenario, '2.0' spec is chosen only for requests which are listed
    in the `prefer_20_routes`. This helps in incremental migration of
    routes from v1.2 to v2.0 by making moving to v2.0 opt-in.

    :rtype: (:class:`SwaggerHandler`,
             :class:`pyramid_swagger.model.SwaggerSchema` OR
                :class:`bravado_core.spec.Spec`)
    """
    enabled_swagger_versions = get_swagger_versions(registry.settings)
    schema12 = registry.settings['pyramid_swagger.schema12']
    schema20 = registry.settings['pyramid_swagger.schema20']

    fallback_to_swagger12_route = (
        SWAGGER_20 in enabled_swagger_versions and
        SWAGGER_12 in enabled_swagger_versions and
        settings.prefer_20_routes and
        route_info.get('route') and
        route_info['route'].name not in settings.prefer_20_routes
    )
    if fallback_to_swagger12_route:
        return settings.swagger12_handler, schema12

    if SWAGGER_20 in enabled_swagger_versions:
        return settings.swagger20_handler, schema20

    if SWAGGER_12 in enabled_swagger_versions:
        return settings.swagger12_handler, schema12


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
        swagger_handler, spec = get_swagger_objects(settings, route_info,
                                                    registry)

        if should_exclude_request(settings, request, route_info):
            return handler(request)

        validation_context = _get_validation_context(registry)

        try:
            op_or_validators_map = swagger_handler.op_for_request(
                request, route_info=route_info, spec=spec)
        except PathNotMatchedError as exc:
            if settings.validate_path:
                with validation_context(request):
                    raise PathNotFoundError(str(exc), child=exc)
            else:
                return handler(request)

        if settings.validate_request:
            with validation_context(request, response=None):
                request_data = swagger_handler.handle_request(
                    PyramidSwaggerRequest(request, route_info),
                    op_or_validators_map,
                )

            def swagger_data(_):
                return request_data

            request.set_property(swagger_data)

        response = handler(request)

        if settings.validate_response:
            with validation_context(request, response=response):
                swagger_handler.handle_response(response, op_or_validators_map)

        return response

    return validator_tween


class PyramidSwaggerRequest(IncomingRequest):
    """Adapter for a :class:`pyramid.request.Request` which exposes request
    data for casting and validation.

    The following properties are exposed in order to comply with the interface
    of :class:`bravado_core.request.IncomingRequest`:

        path: a dictionary of URL path parameters
        query: a dictionary of parameters from the query string
        form: a dictionary of form parameters from a POST
        headers: a dictionary of request headers
        files: a dictionary of uploaded filename to content
    """

    FORM_TYPES = [
        'application/x-www-form-urlencoded',
        'multipart/form-data',
    ]

    def __init__(self, request, route_info):
        """
        :type request: :class:`pyramid.request.Request`
        :type route_info: :class:`pyramid.urldispatch.Route`
        """
        self.request = request
        self.route_info = route_info

    @property
    def headers(self):
        return self.request.headers

    @property
    def query(self):
        """
        :rtype: dict
        """
        # The `mixed` dict will return a list if a parameter has multiple
        # values or a single primitive in the case of a single value.
        return self.request.GET.mixed()

    @property
    def path(self):
        return self.route_info.get('match') or {}

    @property
    def form(self):
        """
        :rtype: dict
        """
        # Don't read the POST dict unless the body is form encoded
        if self.request.content_type in self.FORM_TYPES:
            return self.request.POST.mixed()
        return {}

    @property
    def body(self):
        return self.json()

    @property
    def files(self):
        result = {}
        for k, v in self.request.params.mixed().items():
            if hasattr(v, 'file'):
                result[k] = v.file
        return result

    def json(self, **kwargs):
        return getattr(self.request, 'json_body', {})


class PyramidSwaggerResponse(OutgoingResponse):
    """Adapter for a :class:`pyramid.response.Response` which exposes response
    data for validation.

    The following properties are exposed in order to comply with the interface
    of :class:`bravado_core.response.OutgoingResponse`:

        content_type: a standard content-type string
        text: the response body as a string
        headers: a dictionary of response headers
    """

    def __init__(self, response):
        """
        :type response: :class:`pyramid.response.Response`
        """
        self.response = response

    @property
    def content_type(self):
        return self.response.content_type

    @property
    def headers(self):
        return self.response.headers

    @property
    def text(self):

        # Treating webob.Response carefully: first check if there's a
        # non-empty body attribute, since if not, we can short circuit
        if not self.response.body:
            return None
        # if there's a response body, try to read it as text, but carefully
        try:
            return self.response.text
        except AttributeError as prev_ex:
            # pyramid.response.Response raises AttributeError if you try to
            # read this property without setting the charset first: trap that
            # so it doesn't show up as a missing "text" attribute (and get
            # its error message swallowed by the base class)
            raise Exception(str(prev_ex))

    def json(self, **kwargs):
        return getattr(self.response, 'json_body', {})


def handle_request(request, validator_map, **kwargs):
    """Validate the request against the swagger spec and return a dict with
    all parameter values available in the request, casted to the expected
    python type.

    :param request: a :class:`PyramidSwaggerRequest` to validate
    :param validator_map: a :class:`pyramid_swagger.load_schema.ValidatorMap`
        used to validate the request
    :returns: a :class:`dict` of request data for each parameter in the swagger
        spec
    :raises: RequestValidationError when the request is not valid for the
        swagger spec
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

    validate_request(validation_pairs)

    return request_data


def load_settings(registry):
    return Settings(
        swagger12_handler=build_swagger12_handler(
            registry.settings.get('pyramid_swagger.schema12')),
        swagger20_handler=build_swagger20_handler(),
        validate_request=asbool(registry.settings.get(
            'pyramid_swagger.enable_request_validation',
            True,
        )),
        validate_response=asbool(registry.settings.get(
            'pyramid_swagger.enable_response_validation',
            True,
        )),
        validate_path=asbool(registry.settings.get(
            'pyramid_swagger.enable_path_validation',
            True,
        )),
        exclude_paths=get_exclude_paths(registry),
        exclude_routes=set(aslist(registry.settings.get(
            'pyramid_swagger.exclude_routes',
        ) or [])),
        prefer_20_routes=set(aslist(registry.settings.get(
            'pyramid_swagger.prefer_20_routes') or [])),
    )


SwaggerHandler = namedtuple('SwaggerHandler',
                            'op_for_request handle_request handle_response')


def build_swagger20_handler():
    return SwaggerHandler(
        op_for_request=get_op_for_request,
        handle_request=swaggerize_request,
        handle_response=swaggerize_response,
    )


def build_swagger12_handler(schema):
    """Builds a swagger12 handler or returns None if no schema is present.

    :type schema: :class:`pyramid_swagger.model.SwaggerSchema`
    :rtype: :class:`SwaggerHandler` or None
    """
    if schema:
        return SwaggerHandler(
            op_for_request=schema.validators_for_request,
            handle_request=handle_request,
            handle_response=validate_response,
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


def is_swagger_documentation_route(route_info):
    if not route_info:
        return False

    route = route_info.get('route')
    if not route:
        return False
    return route.name.startswith('pyramid_swagger.swagger20.api_docs.')


def should_exclude_request(settings, request, route_info):
    disable_all_validation = not any((
        settings.validate_request,
        settings.validate_response,
        settings.validate_path
    ))
    return (
        disable_all_validation or
        should_exclude_path(settings.exclude_paths, request.path_info) or
        should_exclude_route(settings.exclude_routes, route_info) or
        is_swagger_documentation_route(route_info)
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
            except (jsonschema.exceptions.ValidationError,
                    SwaggerMappingError) as exc:
                # This will alter our stack trace slightly, but Pyramid knows
                # how to render it. And the real value is in the message
                # anyway.
                e = exc_class(str(exc), child=exc)
                e._traceback = sys.exc_info()[2]
                raise e

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
def validate_response(response, validator_map):
    """Validates response against our schemas.

    :param response: the response object to validate
    :type response: :class:`pyramid.response.Response`
    :type validator_map: :class:`pyramid_swagger.load_schema.ValidatorMap`
    """
    validator = validator_map.response

    # Short circuit if we are supposed to not validate anything.
    returns_nothing = validator.schema.get('type') == 'void'
    body_empty = response.body in (None, b'', b'{}', b'null')
    if returns_nothing and body_empty:
        return

    # Don't attempt to validate non-success responses in v1.2
    if not 200 <= response.status_code <= 203:
        return

    validator.validate(prepare_body(response))


def prepare_body(response):
    # content_type must be set to access response.text
    if not response.content_type:
        raise ResponseValidationError(
            'Response validation error: Content-Type must be set'
        )

    if 'application/json' in response.content_type:
        return simplejson.loads(response.text)
    else:
        return response.text


@validation_error(RequestValidationError)
def swaggerize_request(request, op, **kwargs):
    """
    Delegate handling the Swagger concerns of the request to bravado-core.
    Post-invocation, the Swagger request parameters are available as a dict
    named `swagger_data` on the Pyramid request.

    :type request: :class:`pyramid.request.Request`
    :type op: :class:`bravado_core.operation.Operation`
    """
    request_data = unmarshal_request(request, op)
    return request_data


@validation_error(ResponseValidationError)
def swaggerize_response(response, op):
    """
    Delegate handling the Swagger concerns of the response to bravado-core.

    :type response: :class:`pyramid.response.Response`
    :type op: :class:`bravado_core.operation.Operation`
    """
    response_spec = get_response_spec(response.status_int, op)
    bravado_core.response.validate_response(
        response_spec, op, PyramidSwaggerResponse(response))


def get_op_for_request(request, route_info, spec):
    """
    Find out which operation in the Swagger schema corresponds to the given
    pyramid request.

    :type request: :class:`pyramid.request.Request`
    :type route_info: dict (usually has 'match' and 'route' keys)
    :type spec: :class:`bravado_core.spec.Spec`
    :rtype: :class:`bravado_core.operation.Operation`
    :raises: PathNotMatchedError when a matching Swagger operation is not
        found.
    """
    # pyramid.urldispath.Route
    route = route_info['route']
    if hasattr(route, 'path'):
        route_path = route.path
        if route_path[0] != '/':
            route_path = '/' + route_path
        op = spec.get_op_for_request(request.method, route_path)
        if op is not None:
            return op
        else:
            raise PathNotMatchedError(
                "Could not find a matching Swagger "
                "operation for {0} request {1}"
                .format(request.method, request.url))
    else:
        raise PathNotMatchedError(
            "Could not find a matching route for {0} request {1}. "
            "Have you registered this endpoint with Pyramid?"
            .format(request.method, request.url))


def get_swagger_versions(settings):
    """
    Validates and returns the versions of the Swagger Spec that this pyramid
    application supports.

    :type settings: dict
    :return: list of strings. eg ['1.2', '2.0']
    :raises: ValueError when an unsupported Swagger version is encountered.
    """
    swagger_versions = set(aslist(settings.get(
        'pyramid_swagger.swagger_versions', DEFAULT_SWAGGER_VERSIONS)))

    if len(swagger_versions) == 0:
        raise ValueError('pyramid_swagger.swagger_versions is empty')

    for swagger_version in swagger_versions:
        if swagger_version not in SUPPORTED_SWAGGER_VERSIONS:
            raise ValueError('Swagger version {0} is not supported.'
                             .format(swagger_version))
    return swagger_versions
