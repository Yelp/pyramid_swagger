# -*- coding: utf-8 -*-
"""
Import this module to add the validation tween to your pyramid app.
"""
import pyramid
from .api import register_api_doc_endpoints
from .ingest import get_swagger_schema


def includeme(config):
    settings = config.registry.settings

    # Add the SwaggerSchema to settings to make it avialable to the validation
    # tween and `register_api_doc_endpoints`
    settings['pyramid_swagger.schema'] = get_swagger_schema(settings)

    config.add_tween(
        "pyramid_swagger.tween.validation_tween_factory",
        under=pyramid.tweens.EXCVIEW
    )

    if settings.get('pyramid_swagger.enable_api_doc_views', True):
        register_api_doc_endpoints(config)
