# -*- coding: utf-8 -*-
"""
Import this module to add the validation tween to your pyramid app.
"""
import pyramid
from .api import register_api_doc_endpoints
from .ingest import compile_swagger_schema
from .spec import validate_swagger_schema


def includeme(config):
    settings = config.registry.settings
    schema_dir = settings.get('pyramid_swagger.schema_directory', 'api_docs/')

    if settings.get('pyramid_swagger.enable_swagger_spec_validation', True):
        validate_swagger_schema(schema_dir)

    # Add the SwaggerSchema to settings to make it avialable to the validation
    # tween and `register_api_doc_endpoints`
    if 'pyramid_swagger.schema' not in settings:
        settings['pyramid_swagger.schema'] = compile_swagger_schema(schema_dir)

    config.add_tween(
        "pyramid_swagger.tween.validation_tween_factory",
        under=pyramid.tweens.EXCVIEW
    )

    if settings.get('pyramid_swagger.enable_api_doc_views', True):
        register_api_doc_endpoints(config)
