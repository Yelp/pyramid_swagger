# -*- coding: utf-8 -*-
import jsonschema.exceptions
import pytest

import sys
import simplejson
from pyramid_swagger.spec import validate_api_declaration
from pyramid_swagger.spec import validate_resource_listing


@pytest.mark.skipif(sys.version_info >= (3, 2), reason='See Issue #20')
def test_resource_listing_validation():
    with open('tests/sample_schemas/good_app/api_docs.json') as f:
        sample_json = simplejson.load(f)
    validate_resource_listing(sample_json)


@pytest.mark.skipif(sys.version_info >= (3, 2), reason='See Issue #20')
def test_resource_listing_validation_on_api_with_bad_resource():
    """Despite having an invalidly constructed resource, this validation should
    succeed."""
    with open('tests/sample_schemas/bad_app/api_docs.json') as f:
        sample_json = simplejson.load(f)
    validate_resource_listing(sample_json)


@pytest.mark.skipif(sys.version_info >= (3, 2), reason='See Issue #20')
def test_api_declaration_validation():
    with open('tests/sample_schemas/good_app/sample.json') as f:
        sample_json = simplejson.load(f)
    validate_api_declaration(sample_json)


@pytest.mark.skipif(sys.version_info >= (3, 2), reason='See Issue #20')
def test_api_declaration_validation_on_invalid_api():
    with open('tests/sample_schemas/bad_app/bad_sample.json') as f:
        sample_json = f.read()
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validate_api_declaration(sample_json)
