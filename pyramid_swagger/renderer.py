# -*- coding: utf-8 -*-
"""
This model contains the main factory of renderers to use while dealing with Swagger 2.0 endpoints.
"""
from __future__ import absolute_import

from functools import partial

from bravado_core.exception import MatchingResponseNotFound
from bravado_core.exception import SwaggerMappingError
from bravado_core.marshal import marshal_schema_object
from bravado_core.response import get_response_spec
from pyramid.renderers import JSON


class PyramidSwaggerRendererFactory(object):
    def __init__(self, renderer_factory=JSON()):
        self.renderer_factory = renderer_factory

    def _marshal_object(self, request, response_object):
        # operation attribute is injected by validator_tween in case the endpoint is served by Swagger 2.0 specs
        operation = getattr(request, 'operation', None)

        if not operation:
            # If the request is not served by Swagger2.0 endpoint _marshal_object is NO_OP
            return response_object

        try:
            response_spec = get_response_spec(
                status_code=request.response.status_code,
                op=request.operation,
            )
            return marshal_schema_object(
                swagger_spec=request.registry.settings['pyramid_swagger.schema20'],
                schema_object_spec=response_spec['schema'],
                value=response_object,
            )
        except (MatchingResponseNotFound, SwaggerMappingError, KeyError):
            # marshaling process failed
            return response_object

    def _render(self, external_renderer, value, system):
        value = self._marshal_object(system['request'], value)
        return external_renderer(value, system)

    def __call__(self, info):
        return partial(self._render, self.renderer_factory(info))
