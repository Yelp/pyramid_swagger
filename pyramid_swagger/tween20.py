# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import namedtuple
import logging
import sys

from bravado_core.exception import SwaggerMappingError
from bravado_core.request import RequestLike, unmarshal_request
from bravado_core.response import validate_response, OutgoingResponse
from pyramid.interfaces import IRoutesMapper
from pyramid_swagger.exceptions import RequestValidationError
from pyramid_swagger.exceptions import ResponseValidationError
from pyramid_swagger.model import PathNotMatchedError
from pyramid_swagger.tween import get_exclude_paths, should_exclude_request
from pyramid_swagger.tween import validation_error, _get_validation_context


log = logging.getLogger(__name__)


class Settings(namedtuple(
    'Settings',
    [
        'spec',
        'validate_request',
        'validate_response',
        'validate_path',
        'exclude_paths',
        'exclude_routes',
    ]
)):

    """A settings object for configurable options.

    :param spec: a :class:`bravado_core.spec.Spec`
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


def swagger_tween_factory(handler, registry):
    """Pyramid tween for performing marshaling, transforming, and validating
    Swagger 2.0 requests and responses.

    :type handler: function
    :type registry: :class:`pyramid.registry.Registry`
    """
    settings = load_settings(registry)
    route_mapper = registry.queryUtility(IRoutesMapper)

    def swagger_tween(request):
        """
        :type request: :class:`pyramid.request.Request`
        """
        route_info = route_mapper(request)

        if should_exclude_request(settings, request, route_info):
            return handler(request)

        validation_context = _get_validation_context(registry)

        try:
            op = swaggerize_request(request, settings, route_info)
        except (PathNotMatchedError, RequestValidationError) as exc:

            # raise existing RVE or allow validation_context to override
            if isinstance(exc, RequestValidationError):
                with validation_context(request):
                    raise

            # PathNotMatched error converts to RVE unless validation context
            # overrides
            if settings.validate_path:
                with validation_context(request):
                    raise RequestValidationError(str(exc)), \
                        None, sys.exc_info()[2]
            else:
                return handler(request)

        response = handler(request)

        with validation_context(request, response=response):
            swaggerize_response(response, settings, op)

        return response

    return swagger_tween


class PyramidSwaggerRequest(RequestLike):
    """Adapter for a :class:`pyramid.request.Request` which exposes request
    data for unmarshaling, transformation, and validation.
    """
    def __init__(self, request, route_info):
        """
        :type request: :class:`pyramid.request.Request`
        :type route_info: :class:`pyramid.urldispatch.Route`
        """
        self.request = request
        self.route_info = route_info

    @property
    def query(self):
        """
        :rtype: dict
        """
        # The `mixed` dict will return a list if a parameter has multiple
        # values or a single primitive in the case of a single value.
        return self.request.GET.mixed()

    @property
    def form(self):
        """
        :rtype: dict
        """
        return self.request.POST.mixed()

    @property
    def files(self):
        result = {}
        for k, v in self.request.params.mixed():
            if hasattr(v, 'file'):
                result[k] = v.file
        return result

    @property
    def path(self):
        return self.route_info.get('match') or {}

    @property
    def headers(self):
        return self.request.headers

    def json(self, **kwargs):
        return getattr(self.request, 'json_body', {})


class PyramidSwaggerResponse(OutgoingResponse):
    """Adapter for a :class:`pyramid.response.Response` which exposes response
    data for validation.
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
    def text(self):
        return self.response.text

    def json(self, **kwargs):
        return getattr(self.response, 'json_body', {})


@validation_error(RequestValidationError)
def swaggerize_request(request, settings, route_info):
    """
    Delegate handling the Swagger concerns of the request to bravado-core.
    Post-invocation, the Swagger request parameters are available as a dict
    named `swagger_data` on the Pyramid request.

    :type request: :class:`pyramid.request.Request`
    :type settings: :class:`Settings`
    :type route_info: :class:`pyramid.urldispatch.Route`
    :rtype: :class:`bravado_core.operation.Operation`
    """
    op = get_op_for_request(request, route_info, settings.spec)
    bravado_request = PyramidSwaggerRequest(request, route_info)
    request_data = unmarshal_request(bravado_request, op)

    def swagger_data(_):
        return request_data

    request.set_property(swagger_data)
    return op


@validation_error(ResponseValidationError)
def swaggerize_response(response, settings, op):
    """
    Delegate handling the Swagger concerns of the response to bravado-core.

    :type response: :class:`pyramid.response.Response`
    :type settings: :class:`Settings`
    :type op: :class:`bravado_core.operation.Operation`
    """
    from bravado_core.response import get_response_spec
    try:
        response_spec = get_response_spec(response.status_int, op)
    except SwaggerMappingError:
        error = ResponseValidationError(
            "Could not find a matching Swagger response for {0} request {1}"
            "with http_status {2}."
            .format(op.http_method.upper(), op.path_name, response.status_code))
        raise error, None, sys.excinfo()[2]

    outgoing_response = PyramidSwaggerResponse(response)
    validate_response(response_spec, op, outgoing_response)


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
        op = spec.get_op_for_request(request.method, route.path)
        if op is not None:
            return op

    raise PathNotMatchedError(
        "Could not find a matching Swagger operation for {0} request {1}"
        .format(request.method, request.url))


def load_settings(registry):
    """
    :type registry: :class:`pyramid.registery.Registry`
    :rtype: :class:`Settings`
    """
    return Settings(
        spec=registry.settings['pyramid_swagger.spec'],
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
