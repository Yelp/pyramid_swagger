# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import functools
import logging
import re
import sys
from collections import namedtuple
from contextlib import contextmanager

import bravado_core
import jsonschema.exceptions
import six
from bravado_core.exception import SwaggerMappingError
from bravado_core.exception import SwaggerSecurityValidationError
from bravado_core.formatter import SwaggerFormat  # noqa: F401
from bravado_core.operation import Operation
from bravado_core.request import IncomingRequest
from bravado_core.request import unmarshal_request
from bravado_core.response import get_response_spec
from bravado_core.response import OutgoingResponse
from pyramid.interfaces import IRoutesMapper
from pyramid.settings import asbool
from pyramid.settings import aslist

from pyramid_swagger.exceptions import PathNotFoundError
from pyramid_swagger.exceptions import RequestAuthenticationError
from pyramid_swagger.exceptions import RequestValidationError
from pyramid_swagger.exceptions import ResponseValidationError
from pyramid_swagger.model import PathNotMatchedError


log = logging.getLogger(__name__)


SWAGGER_20 = '2.0'
DEFAULT_SWAGGER_VERSIONS = [SWAGGER_20]
SUPPORTED_SWAGGER_VERSIONS = [SWAGGER_20]


DEFAULT_EXCLUDED_PATHS = [
    r'^/static/?',
    r'^/api-docs/?',
    r'^/swagger.(json|yaml)',
]


class Settings(namedtuple(
    'Settings',
    [
        'swagger20_handler',
        'validate_request',
        'validate_response',
        'validate_path',
        'exclude_paths',
        'exclude_routes',
    ]
)):

    """A settings object for configurable options.

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
            r'(?P<module_path>.*)\.(?P<contextmanager_name>.*)',
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


def get_swagger_objects(settings, registry):
    """Returns appropriate swagger handler and swagger spec schema.

    Swagger Handler contains callables that isolate implementation differences
    in the tween to handle both Swagger 1.2 and Swagger 2.0.

    :rtype: (:class:`SwaggerHandler`,
             :class:`bravado_core.spec.Spec`)
    """
    enabled_swagger_versions = get_swagger_versions(registry.settings)
    schema20 = registry.settings['pyramid_swagger.schema20']

    if SWAGGER_20 in enabled_swagger_versions:
        return settings.swagger20_handler, schema20


def validation_tween_factory(handler, registry):
    """Pyramid tween for performing validation.

    Note this is very simple -- it validates requests, responses, and paths
    while delegating to the relevant matching view.
    """
    settings = load_settings(registry)
    route_mapper = registry.queryUtility(IRoutesMapper)

    validation_context = _get_validation_context(registry)

    def validator_tween(request):
        # We don't have access to this yet but let's go ahead and build the
        # matchdict so we can validate it and use it to exclude routes from
        # validation.
        route_info = route_mapper(request)
        swagger_handler, spec = get_swagger_objects(settings, registry)

        if should_exclude_request(settings, request, route_info):
            return handler(request)

        try:
            op_or_validators_map = swagger_handler.op_for_request(
                request, route_info=route_info, spec=spec)
        except PathNotMatchedError as exc:
            if settings.validate_path:
                with validation_context(request):
                    raise PathNotFoundError(str(exc), child=exc)
            else:
                return handler(request)

        def operation(_):
            return op_or_validators_map if isinstance(op_or_validators_map, Operation) else None

        request.set_property(operation)

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
        if self.request.is_body_readable:
            return getattr(self.request, 'json_body', {})
        else:
            return None


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
    def raw_bytes(self):
        return self.response.body

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


def load_settings(registry):
    return Settings(
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
    )


SwaggerHandler = namedtuple('SwaggerHandler',
                            'op_for_request handle_request handle_response')


def build_swagger20_handler():
    return SwaggerHandler(
        op_for_request=get_op_for_request,
        handle_request=swaggerize_request,
        handle_response=swaggerize_response,
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
        disable_all_validation
        or should_exclude_path(settings.exclude_paths, request.path_info)
        or should_exclude_route(settings.exclude_routes, route_info)
        or is_swagger_documentation_route(route_info)
    )


def should_exclude_path(exclude_path_regexes, path):
    # Skip validation for the specified endpoints
    return any(r.match(path) for r in exclude_path_regexes)


def should_exclude_route(excluded_routes, route_info):
    return route_info.get('route') and route_info['route'].name in excluded_routes


def validation_error(exc_class):
    def decorator(f):
        @functools.wraps(f)
        def _validate(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except (
                jsonschema.exceptions.ValidationError,
                SwaggerMappingError,
            ) as exc:
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


@validation_error(RequestValidationError)
def swaggerize_request(request, op, **kwargs):
    """
    Delegate handling the Swagger concerns of the request to bravado-core.
    Post-invocation, the Swagger request parameters are available as a dict
    named `swagger_data` on the Pyramid request.

    :type request: :class:`pyramid.request.Request`
    :type op: :class:`bravado_core.operation.Operation`
    :raises: RequestValidationError, RequestAuthenticationError
    """
    try:
        request_data = unmarshal_request(request, op)
    except SwaggerSecurityValidationError as e:
        six.raise_from(RequestAuthenticationError(e), e)
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
    application supports. (currently only support 2.0)

    :type settings: dict
    :return: list of strings. eg ['2.0']
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
