# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import namedtuple
import functools
import logging

import jsonschema.exceptions
from pyramid.interfaces import IRoutesMapper

from bravado.mapping.request import RequestLike, unmarshal_request
from pyramid_swagger.exceptions import RequestValidationError
from pyramid_swagger.exceptions import ResponseValidationError
from pyramid_swagger.tween import get_exclude_paths, should_exclude_request

log = logging.getLogger(__name__)


DEFAULT_EXCLUDED_PATHS = [
    r'^/static/?',
    r'^/api-docs/?'
]


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

    """A settings object for configuratble options.

    :param spec: a :class:`bravado.mapping.spec.Spec`
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

        # TODO: Remove try/except
        try:
            swaggerize_request(request, settings, route_info)
        except Exception as e:
            import traceback, sys
            traceback.print_exc(file=sys.stdout)
            raise

        response = handler(request)
        swaggerize_response(response)
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


@validation_error(RequestValidationError)
def swaggerize_request(request, settings, route_info):
    """
    Delegate handling the Swagger concerns of the request to bravado-core.
    Post-invocation, the Swagger request parameters are available as a dict
    named `swagger_data` on the Pyramid request.

    :type request: :class:`pyramid.request.Request`
    :type settings: :class:`Settings`
    :type route_info: :class:`pyramid.urldispatch.Route`
    """
    op = get_operation_for_request(request, route_info, settings.spec)
    bravado_request = PyramidSwaggerRequest(request, route_info)
    request_data = unmarshal_request(bravado_request, op)

    def swagger_data(_):
        return request_data

    request.set_property(swagger_data)


@validation_error(ResponseValidationError)
def swaggerize_response(response):
    """
    Delegate handling the Swagger concerns of the response to bravado-core.

    :type response: :class:`pyramid.response.Response`
    """
    # TODO: validate, marshal, and transform the response object
    pass


def get_operation_for_request(request, route_info, spec):
    """
    Find out which operation in the Swagger schema corresponds to the given
    pyramid request.

    :type request: :class:`pyramid.request.Request`
    :type route_info: :class:`pyramid.urldispatch.Route`
    :type spec: :class:`bravado.mapping.spec.Spec`
    :rtype: :class:`bravado.mapping.operation.Operation`
    :raises: RequestValidationError when a matching Swagger operation is not
        found.
    """
    # TODO: cache in a map using a composite key so lookup is not done on every
    #       request
    resource_map = spec.resources
    for resource_name, resource in resource_map.iteritems():
        op_map = resource.operations
        for op_name, op in op_map.iteritems():
            if op.http_method.lower() == request.method.lower():
                route = route_info['route']
                if route.path == op.path_name:
                    return op
    raise RequestValidationError(
        detail="Could not find a matching Swagger operation for {0} request "
               "with path {1}.".format(request.method, route.path))


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
