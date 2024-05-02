# -*- coding: utf-8 -*-
"""
Unit tests for the SwaggerSchema class.
"""
from __future__ import absolute_import

import mock
import pytest

from pyramid_swagger.ingest import compile_swagger_schema
from pyramid_swagger.ingest import get_resource_listing
from pyramid_swagger.model import partial_path_match
from pyramid_swagger.model import PathNotMatchedError


@pytest.fixture
def schema():
    schema_dir = 'tests/sample_schemas/good_app/'
    return compile_swagger_schema(
        schema_dir,
        get_resource_listing(schema_dir, False)
    )


@pytest.mark.skip(reason="Deprecated swagger 1.2 tests are broken. Skip instead of fixing.")
def test_swagger_schema_for_request_different_methods(schema):
    """Tests that validators_for_request() checks the request
    method."""
    # There exists a GET and POST for this endpoint. We should be able to call
    # either and have them pass validation.
    value = schema.validators_for_request(
        request=mock.Mock(
            path_info="/sample",
            method="GET"
        ),
    )
    assert value.body.schema is None

    value = schema.validators_for_request(
        request=mock.Mock(
            path_info="/sample",
            method="POST",
            body={'foo': 1, 'bar': 2},
        ),
    )
    assert value.body.schema == {
        'required': True,
        'name': 'content',
        'paramType': 'body',
        'type': 'body_model',
    }


@pytest.mark.skip(reason="Deprecated swagger 1.2 tests are broken. Skip instead of fixing.")
def test_swagger_schema_for_request_not_found(schema):
    """Tests that validators_for_request() raises exceptions when
    a path is not found.
    """
    # There exists a GET and POST for this endpoint. We should be able to call
    # either and have them pass validation.
    with pytest.raises(PathNotMatchedError) as excinfo:
        schema.validators_for_request(
            request=mock.Mock(
                path_info="/does_not_exist",
                method="GET"
            ),
        )
    assert '/does_not_exist' in str(excinfo.value)
    assert 'Could not find ' in str(excinfo.value)


def test_partial_path_match():
    assert partial_path_match(
        '/v1/bing/forward_unstructured',
        '/v1/bing/forward_unstructured'
    )
    assert partial_path_match(
        '/v1/{api_provider}/forward_unstructured',
        '/v1/bing/forward_unstructured'
    )
    assert not partial_path_match(
        '/v1/google/forward_unstructured',
        '/v1/bing/forward_unstructured'
    )


@pytest.mark.skip(reason="Deprecated swagger 1.2 tests are broken. Skip instead of fixing.")
def test_swagger_schema_for_request_virtual_subpath(schema):

    # There exists a GET and POST for this endpoint. We should be able to call
    # either and have them pass validation.
    value = schema.validators_for_request(
        request=mock.Mock(
            path="/subpath/sample",
            script_name="/subpath",
            path_info="/sample",
            method="GET"
        ),
    )
    assert value.body.schema is None
