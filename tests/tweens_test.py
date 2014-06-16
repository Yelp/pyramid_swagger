# -*- coding: utf-8 -*-
"""Unit tests for tweens.py"""
import mock
import pytest
from pyramid.httpexceptions import HTTPClientError

from pyramid_swagger.tween import swagger_schema_for_request


def test_swagger_schema_for_request_different_methods():
    """Tests that swagger_schema_for_request() checks the request method."""
    mock_request = mock.Mock(
        path="/foo/bar",
        method="GET"
    )
    mock_schema_map = mock.Mock(items=mock.Mock(return_value=[
        (('/foo/{bars}', 'PUT'), 1234),
        (('/foo/{bars}', 'GET'), 666)
    ]))
    value = swagger_schema_for_request(mock_request, mock_schema_map)
    assert value == 666


def test_swagger_schema_for_request_not_found():
    """Tests that swagger_schema_for_request() raises exceptions when
    a path is not found.
    """
    mock_request = mock.Mock(
        path="/foo/bar",
        method="GET"
    )
    mock_schema_map = mock.Mock(items=mock.Mock(return_value=[]))
    with pytest.raises(HTTPClientError) as excinfo:
        swagger_schema_for_request(mock_request, mock_schema_map)
    assert '/foo/bar' in str(excinfo)
    assert 'Could not find ' in str(excinfo)
