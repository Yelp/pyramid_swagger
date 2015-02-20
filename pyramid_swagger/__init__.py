# -*- coding: utf-8 -*-
"""
Import this module to add the validation tween to your pyramid app.
"""
import pyramid
from .api import register_api_doc_endpoints
from .ingest import add_swagger_schema


def includeme(config):
    add_swagger_schema(config.registry)

    config.add_tween(
        "pyramid_swagger.tween.validation_tween_factory",
        under=pyramid.tweens.EXCVIEW
    )

    if config.registry.settings.get(
        'pyramid_swagger.enable_api_doc_views',
        True
    ):
        register_api_doc_endpoints(config)
