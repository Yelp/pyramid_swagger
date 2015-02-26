# -*- coding: utf-8 -*-
import pytest
from pyramid_swagger.ingest import API_DOCS_FILENAME
from pyramid_swagger.ingest import _load_resource_listing
from pyramid_swagger.ingest import ingest_resources
from pyramid_swagger.ingest import ApiDeclarationNotFoundError
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
