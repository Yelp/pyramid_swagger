# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import os.path

from bravado_core.spec import build_http_handlers
from bravado_core.spec import Spec
from six import iteritems
from six.moves.urllib import parse as urlparse
from six.moves.urllib.request import pathname2url


# Prefix of configs that will be passed to the underlying bravado-core instance
BRAVADO_CORE_CONFIG_PREFIX = 'bravado_core.'


def get_swagger_spec(settings):
    """Return a :class:`bravado_core.spec.Spec` constructed from
    the swagger specs in `pyramid_swagger.schema_directory`. If
    `pyramid_swagger.enable_swagger_spec_validation` is enabled the schema
    will be validated before returning it.

    :param settings: a pyramid registry settings with configuration for
        building a swagger schema
    :type settings: dict
    :rtype: :class:`bravado_core.spec.Spec`
    """
    schema_dir = settings.get('pyramid_swagger.schema_directory', 'api_docs/')
    schema_filename = settings.get('pyramid_swagger.schema_file',
                                   'swagger.json')
    schema_path = os.path.join(schema_dir, schema_filename)
    schema_url = urlparse.urljoin('file:', pathname2url(os.path.abspath(schema_path)))

    handlers = build_http_handlers(None)  # don't need http_client for file:
    file_handler = handlers['file']
    spec_dict = file_handler(schema_url)

    return Spec.from_dict(
        spec_dict,
        config=create_bravado_core_config(settings),
        origin_url=schema_url)


def create_bravado_core_config(settings):
    """Create a configuration dict for bravado_core based on pyramid_swagger
    settings.

    :param settings: pyramid registry settings with configuration for
        building a swagger schema
    :type settings: dict
    :returns: config dict suitable for passing into
        bravado_core.spec.Spec.from_dict(..)
    :rtype: dict
    """
    # Map pyramid_swagger config key -> bravado_core config key
    config_keys = {
        'pyramid_swagger.enable_request_validation': 'validate_requests',
        'pyramid_swagger.enable_response_validation': 'validate_responses',
        'pyramid_swagger.enable_swagger_spec_validation': 'validate_swagger_spec',
        'pyramid_swagger.use_models': 'use_models',
        'pyramid_swagger.user_formats': 'formats',
        'pyramid_swagger.include_missing_properties': 'include_missing_properties',
    }

    configs = {
        'use_models': False,
    }
    configs.update({
        bravado_core_key: settings[pyramid_swagger_key]
        for pyramid_swagger_key, bravado_core_key in iteritems(config_keys)
        if pyramid_swagger_key in settings
    })
    configs.update({
        key.replace(BRAVADO_CORE_CONFIG_PREFIX, ''): value
        for key, value in iteritems(settings)
        if key.startswith(BRAVADO_CORE_CONFIG_PREFIX)
    })

    return configs
