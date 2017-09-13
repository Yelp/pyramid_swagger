# -*- coding: utf-8 -*-
import os.path

import mock
import pytest
import simplejson

from pyramid_swagger.ingest import _load_resource_listing
from pyramid_swagger.ingest import API_DOCS_FILENAME
from pyramid_swagger.ingest import ApiDeclarationNotFoundError
from pyramid_swagger.ingest import create_bravado_core_config
from pyramid_swagger.ingest import generate_resource_listing
from pyramid_swagger.ingest import get_resource_listing
from pyramid_swagger.ingest import get_swagger_schema
from pyramid_swagger.ingest import get_swagger_spec
from pyramid_swagger.ingest import ingest_resources
from pyramid_swagger.ingest import ResourceListingGenerationError
from pyramid_swagger.ingest import ResourceListingNotFoundError
from pyramid_swagger.tween import SwaggerFormat


def test_proper_error_on_missing_resource_listing():
    filename = 'tests/sample_schemas/missing_resource_listing/api_docs.json'
    with pytest.raises(ResourceListingNotFoundError) as exc:
        _load_resource_listing(filename)
    assert filename in str(exc)
    assert 'must be named {0}'.format(API_DOCS_FILENAME) in str(exc)


def test_proper_error_on_missing_api_declaration():
    with pytest.raises(ApiDeclarationNotFoundError) as exc:
        ingest_resources(
            {'sample_resource': 'fake/sample_resource.json'},
            'fake',
        )
    assert 'fake/sample_resource.json' in str(exc)


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


def test_get_swagger_schema_default():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
    }

    swagger_schema = get_swagger_schema(settings)
    assert len(swagger_schema.pyramid_endpoints) == 4
    assert swagger_schema.resource_validators


def test_get_swagger_schema_no_validation():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/bad_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    # No error means we skipped validation of the bad schema
    get_swagger_schema(settings)


def test_generate_resource_listing():
    listing = {'swaggerVersion': 1.2}

    listing = generate_resource_listing(
        'tests/sample_schemas/good_app/',
        listing
    )

    expected = {
        'swaggerVersion': 1.2,
        'apis': [
            {'path': '/no_models'},
            {'path': '/other_sample'},
            {'path': '/sample'},
        ]
    }
    assert listing == expected


def test_generate_resource_listing_with_existing_listing():
    listing = {
        'apis': [{'path': '/something'}]
    }
    with pytest.raises(ResourceListingGenerationError) as exc:
        generate_resource_listing('tests/sample_schemas/good_app/', listing)

    assert 'Generating a listing would override' in str(exc)


@mock.patch('pyramid_swagger.ingest.generate_resource_listing', autospec=True)
@mock.patch('pyramid_swagger.ingest._load_resource_listing', autospec=True)
def test_get_resource_listing_generated(mock_load, mock_generate):
    schema_dir = '/api_docs'
    resource_listing = get_resource_listing(schema_dir, True)
    mock_generate.assert_called_once_with(schema_dir, mock_load.return_value)
    assert resource_listing == mock_generate.return_value


def test_get_resource_listing_default():
    schema_dir = 'tests/sample_schemas/good_app/'
    resource_listing = get_resource_listing(schema_dir, False)

    with open(os.path.join(schema_dir, 'api_docs.json')) as fh:
        assert resource_listing == simplejson.load(fh)


def test_create_bravado_core_config_with_defaults():
    assert {'use_models': False} == create_bravado_core_config({})


def test_create_bravado_core_config_non_empty():
    some_format = mock.Mock(spec=SwaggerFormat)
    pyramid_swagger_config = {
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_response_validation': False,
        'pyramid_swagger.enable_swagger_spec_validation': True,
        'pyramid_swagger.use_models': True,
        'pyramid_swagger.user_formats': [some_format],
        'pyramid_swagger.include_missing_properties': False,
    }
    expected_bravado_core_config = {
        'validate_requests': True,
        'validate_responses': False,
        'validate_swagger_spec': True,
        'use_models': True,
        'formats': [some_format],
        'include_missing_properties': False
    }
    bravado_core_config = create_bravado_core_config(pyramid_swagger_config)
    assert expected_bravado_core_config == bravado_core_config
