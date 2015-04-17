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
    settings['pyramid_swagger.schema'] = get_swagger_schema(settings)
    settings['pyramid_swagger.spec'] = get_swagger_spec(settings)

    config.add_tween(
        # "pyramid_swagger.tween.validation_tween_factory",   # 1.2
        "pyramid_swagger.tween20.swagger_tween_factory",  # 2.0
        under=pyramid.tweens.EXCVIEW
    )

    if settings.get('pyramid_swagger.enable_api_doc_views', True):
        register_api_doc_endpoints(config)
        register_swagger_json_endpoint(config)
