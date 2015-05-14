# -*- coding: utf-8 -*-
import os.path

import mock
import pytest
import simplejson

from pyramid_swagger.ingest import API_DOCS_FILENAME
from pyramid_swagger.ingest import _load_resource_listing
from pyramid_swagger.ingest import generate_resource_listing
from pyramid_swagger.ingest import get_swagger_schema
from pyramid_swagger.ingest import get_resource_listing
from pyramid_swagger.ingest import ingest_resources
from pyramid_swagger.ingest import ApiDeclarationNotFoundError
from pyramid_swagger.ingest import ResourceListingGenerationError
from pyramid_swagger.ingest import ResourceListingNotFoundError


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


@pytest.mark.xfail(reason='Remove 1.2 test')
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
