# -*- coding: utf-8 -*-
"""
Import this module to add the validation tween to your pyramid app.
"""
import pyramid

from .api import register_api_doc_endpoints, build_swagger_20_swagger_dot_json
from .ingest import get_swagger_schema
from .ingest import get_swagger_spec
from .tween import (
    get_swagger_versions, register_user_formatters, SWAGGER_12, SWAGGER_20)


def includeme(config):
    """
    :type config: :class:`pyramid.config.Configurator`
    """
    settings = config.registry.settings
    swagger_versions = get_swagger_versions(settings)

    # Add the SwaggerSchema to settings to make it available to the validation
    # tween and `register_api_doc_endpoints`
    if SWAGGER_12 in swagger_versions:
        # Store under two keys so that 1.2 and 2.0 can co-exist.
        settings['pyramid_swagger.schema'] = \
            settings['pyramid_swagger.schema12'] = get_swagger_schema(settings)

    if SWAGGER_20 in swagger_versions:
        settings['pyramid_swagger.schema'] = get_swagger_spec(settings)
        register_user_formatters(settings)

    config.add_tween(
        "pyramid_swagger.tween.validation_tween_factory",
        under=pyramid.tweens.EXCVIEW
    )

    if settings.get('pyramid_swagger.enable_api_doc_views', True):
        # TODO: add a new setting to pyramid_swagger that allows setting a
        #       different base_path for api_docs, and pass it in here
        if SWAGGER_12 in swagger_versions:
            register_api_doc_endpoints(
                config,
                settings['pyramid_swagger.schema12'].get_api_doc_endpoints())

        if SWAGGER_20 in swagger_versions:
            register_api_doc_endpoints(
                config,
                [build_swagger_20_swagger_dot_json(config)],
                base_path='')
