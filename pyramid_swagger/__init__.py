# -*- coding: utf-8 -*-
"""
Import this module to add the validation tween to your pyramid app.
"""
import pyramid

from .api import register_api_doc_endpoints, build_swagger_20_swagger_dot_json
from .ingest import get_swagger_schema
from .ingest import get_swagger_spec

SWAGGER_12 = '1.2'
SWAGGER_20 = '2.0'
DEFAULT_SWAGGER_VERSIONS = [SWAGGER_20]
SUPPORTED_SWAGGER_VERSIONS = [SWAGGER_12, SWAGGER_20]


def get_swagger_versions(settings):
    """
    Validates and returns the versions of the Swagger Spec that this pyramid
    application supports.

    :type settings: dict
    :return: list of strings. eg ['1.2', '2.0']
    """
    swagger_versions = settings.get(
        'pyramid_swagger.swagger_versions', DEFAULT_SWAGGER_VERSIONS)

    if len(swagger_versions) == 0:
        raise ValueError('pyramid_swagger.swagger_versions is empty')

    for swagger_version in swagger_versions:
        if swagger_version not in SUPPORTED_SWAGGER_VERSIONS:
            raise ValueError('Swagger version {0} is not supported.'
                             .format(swagger_version))
    return swagger_versions


def includeme(config):
    """
    :type config: :class:`pyramid.config.Configurator`
    """
    settings = config.registry.settings

    # Add the SwaggerSchema to settings to make it avialable to the validation
    # tween and `register_api_doc_endpoints`
    swagger_versions = get_swagger_versions(settings)

    if SWAGGER_12 in swagger_versions:
        settings['pyramid_swagger.schema'] = \
            settings['pyramid_swagger.schema12'] = get_swagger_schema(settings)

    if SWAGGER_20 in swagger_versions:
        settings['pyramid_swagger.schema'] = get_swagger_spec(settings)

    config.add_tween(
        "pyramid_swagger.tween.validation_tween_factory",
        under=pyramid.tweens.EXCVIEW
    )

    if settings.get('pyramid_swagger.enable_api_doc_views', True):
        endpoints = []
        if SWAGGER_12 in swagger_versions:
            endpoints += \
                settings['pyramid_swagger.schema12'].get_api_doc_endpoints()

        if SWAGGER_20 in swagger_versions:
            endpoints.append(build_swagger_20_swagger_dot_json(config))

        # TODO: There are competing concerns here - for Swagger 1.2 the schemas
        #       are usually served up under /api-docs for the resource listing
        #       and /api-docs/{resource_name} for the api declarations. For
        #       Swagger 2.0 the default behavior should be to serve up the
        #       schema as /swagger.json. Since register_api_doc_endpoints(..)
        #       uses the same base_path regardless of the endpoint, both use
        #       cases can't be satisfied unless the base_path is coupled with
        #       a given PyramidEndpoint. I've worked around this by changing
        #       the path of the 1.2 endpoints to include /api-docs in the
        #       'path' so that an empty base_path can be passed in to this
        #       function call and behave as expected.

        # TODO: add a new setting to pyramid_swagger that allows setting a
        #       different base_path for api_docs, and pass it in here
        register_api_doc_endpoints(config, endpoints, base_path='')
