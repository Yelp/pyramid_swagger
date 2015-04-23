# -*- coding: utf-8 -*-
"""
Import this module to add the validation tween to your pyramid app.
"""
import pyramid

from .api import register_api_doc_endpoints
from .api import register_swagger_json_endpoint
from .ingest import get_swagger_schema
from .ingest import get_swagger_spec


def includeme(config):
    """
    :type config: :class:`pyramid.config.Configurator`
    """
    settings = config.registry.settings

    # Add the SwaggerSchema to settings to make it avialable to the validation
    # tween and `register_api_doc_endpoints`
    swagger_version = settings.get('pyramid_swagger.swagger_version', '2.0')

    if swagger_version == '1.2':
        settings['pyramid_swagger.schema'] = get_swagger_schema(settings)
    elif swagger_version == '2.0':
        settings['pyramid_swagger.schema'] = get_swagger_spec(settings)
    else:
        raise TypeError('Unsupported pyramid_swagger.swagger_version: {0}'
                        .format(swagger_version))

    config.add_tween(
        "pyramid_swagger.tween.validation_tween_factory",
        under=pyramid.tweens.EXCVIEW
    )

    if settings.get('pyramid_swagger.enable_api_doc_views', True):
        if swagger_version == '1.2':
            register_api_doc_endpoints(config)

        if swagger_version == '2.0':
            register_swagger_json_endpoint(config)
