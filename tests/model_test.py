"""
Unit tests for the SwaggerSchema class.
"""
import mock
import pytest
from pyramid.httpexceptions import HTTPClientError

from pyramid_swagger.model import SwaggerSchema
from pyramid_swagger.model import partial_path_match


def test_swagger_schema_for_request_different_methods():
    """Tests that schema_and_resolver_for_request() checks the request
    method."""
    schema = SwaggerSchema('tests/sample_schemas/good_app/', True)

    # There exists a GET and POST for this endpoint. We should be able to call
    # either and have them pass validation.
    mock_request = mock.Mock(
        path="/sample",
        method="GET"
    )
    value, _ = schema.schema_and_resolver_for_request(mock_request)
    assert value.request_body_schema == None

    mock_request = mock.Mock(
        path="/sample",
        method="POST",
        body={'foo': 1, 'bar': 2},
    )
    value, _ = schema.schema_and_resolver_for_request(mock_request)
    assert (
        value.request_body_schema == {
            'required': True,
            u'$ref': 'body_model'
        }
    )


def test_swagger_schema_for_request_not_found():
    """Tests that schema_and_resolver_for_request() raises exceptions when
    a path is not found.
    """
    schema = SwaggerSchema('tests/sample_schemas/good_app/', True)

    # There exists a GET and POST for this endpoint. We should be able to call
    # either and have them pass validation.
    mock_request = mock.Mock(
        path="/does_not_exist",
        method="GET"
    )
    with pytest.raises(HTTPClientError) as excinfo:
        schema.schema_and_resolver_for_request(mock_request)
    assert '/does_not_exist' in str(excinfo)
    assert 'Could not find ' in str(excinfo)


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
