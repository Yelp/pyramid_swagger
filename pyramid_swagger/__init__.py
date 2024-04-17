# -*- coding: utf-8 -*-
"""
Import this module to add the validation tween to your pyramid app.
"""
from __future__ import absolute_import

import pyramid

from pyramid_swagger.api import build_swagger_20_swagger_schema_views
from pyramid_swagger.api import register_api_doc_endpoints
from pyramid_swagger.ingest import get_swagger_schema
from pyramid_swagger.ingest import get_swagger_spec
from pyramid_swagger.renderer import PyramidSwaggerRendererFactory
from pyramid_swagger.tween import get_swagger_versions
from pyramid_swagger.tween import SWAGGER_12
from pyramid_swagger.tween import SWAGGER_20


def includeme(config):
    """
    :type config: :class:`pyramid.config.Configurator`
    """
    settings = config.registry.settings
    swagger_versions = get_swagger_versions(settings)

    # for rendering /swagger.yaml
    config.add_renderer(
        'yaml', 'pyramid_swagger.api.YamlRendererFactory',
    )

    # Add the SwaggerSchema to settings to make it available to the validation
    # tween and `register_api_doc_endpoints`
    settings['pyramid_swagger.schema12'] = None
    settings['pyramid_swagger.schema20'] = None

    # Store under two keys so that 1.2 and 2.0 can co-exist.
    if SWAGGER_12 in swagger_versions:
        settings['pyramid_swagger.schema12'] = get_swagger_schema(settings)

    if SWAGGER_20 in swagger_versions:
        settings['pyramid_swagger.schema20'] = get_swagger_spec(settings)

    config.add_tween(
        "pyramid_swagger.tween.validation_tween_factory",
        under=pyramid.tweens.EXCVIEW
    )

    config.add_renderer('pyramid_swagger', PyramidSwaggerRendererFactory())

    if pyramid.settings.asbool(
            settings.get('pyramid_swagger.enable_api_doc_views', True)):>>>>>>> master
        if SWAGGER_12 in swagger_versions:
            register_api_doc_endpoints(
                config,
                settings['pyramid_swagger.schema12'].get_api_doc_endpoints())

        if SWAGGER_20 in swagger_versions:
            register_api_doc_endpoints(
                config,
                build_swagger_20_swagger_schema_views(config),
                base_path=settings.get('pyramid_swagger.base_path_api_docs', ''))
