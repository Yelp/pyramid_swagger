# -*- coding: utf-8 -*-
from __future__ import absolute_import

import mock
import pytest

from pyramid_swagger.ingest import BRAVADO_CORE_CONFIG_PREFIX
from pyramid_swagger.ingest import create_bravado_core_config
from pyramid_swagger.ingest import get_swagger_spec
from pyramid_swagger.tween import SwaggerFormat


@mock.patch('pyramid_swagger.ingest.build_http_handlers',
            return_value={'file': mock.Mock()})
@mock.patch('os.path.abspath', return_value='/bar/foo/swagger.json')
@mock.patch('pyramid_swagger.ingest.Spec.from_dict')
def test_get_swagger_spec_passes_absolute_url(
    mock_spec, mock_abs, mock_http_handlers,
):
    get_swagger_spec({'pyramid_swagger.schema_directory': 'foo/'})
    mock_abs.assert_called_once_with('foo/swagger.json')
    expected_url = "file:///bar/foo/swagger.json"
    mock_spec.assert_called_once_with(mock.ANY, config=mock.ANY,
                                      origin_url=expected_url)


def test_create_bravado_core_config_with_defaults():
    assert {'use_models': False} == create_bravado_core_config({})


@pytest.fixture
def bravado_core_formats():
    return [mock.Mock(spec=SwaggerFormat)]


@pytest.fixture
def bravado_core_configs(bravado_core_formats):
    return {
        'validate_requests': True,
        'validate_responses': False,
        'validate_swagger_spec': True,
        'use_models': True,
        'formats': bravado_core_formats,
        'include_missing_properties': False
    }


def test_create_bravado_core_config_non_empty_deprecated_configs(
    bravado_core_formats, bravado_core_configs,
):
    pyramid_swagger_config = {
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_response_validation': False,
        'pyramid_swagger.enable_swagger_spec_validation': True,
        'pyramid_swagger.use_models': True,
        'pyramid_swagger.user_formats': bravado_core_formats,
        'pyramid_swagger.include_missing_properties': False,
    }

    bravado_core_config = create_bravado_core_config(pyramid_swagger_config)

    assert bravado_core_configs == bravado_core_config


def test_create_bravado_core_config_with_passthrough_configs(bravado_core_formats, bravado_core_configs):
    pyramid_swagger_config = {
        '{}validate_requests'.format(BRAVADO_CORE_CONFIG_PREFIX): True,
        '{}validate_responses'.format(BRAVADO_CORE_CONFIG_PREFIX): False,
        '{}validate_swagger_spec'.format(BRAVADO_CORE_CONFIG_PREFIX): True,
        '{}use_models'.format(BRAVADO_CORE_CONFIG_PREFIX): True,
        '{}formats'.format(BRAVADO_CORE_CONFIG_PREFIX): bravado_core_formats,
        '{}include_missing_properties'.format(BRAVADO_CORE_CONFIG_PREFIX): False
    }

    bravado_core_config = create_bravado_core_config(pyramid_swagger_config)

    assert bravado_core_configs == bravado_core_config
