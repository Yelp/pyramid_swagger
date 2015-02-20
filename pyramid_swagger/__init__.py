# -*- coding: utf-8 -*-
"""
Import this module to add the validation tween to your pyramid app.
"""
import pyramid
from .api import register_api_doc_endpoints


def includeme(config):
    config.add_tween(
        "pyramid_swagger.tween.validation_tween_factory",
        under=pyramid.tweens.EXCVIEW
    )
    if config.registry.settings.get(
        'pyramid_swagger.enable_api_doc_views',
        True
    ):
        register_api_doc_endpoints(config)
