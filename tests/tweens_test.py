# -*- coding: utf-8 -*-
"""Unit tests for tweens.py"""
import mock
from pyramid_swagger.tweens import extract_relevant_schema


def test_extract_relevant_schema_diff_methods():
    """Tests that extract_relevant_schema() checks the request method."""
    mock_request = mock.Mock(
        path="/foo/bar",
        method="GET"
    )
    mock_resolver = mock.Mock(schema_map=mock.Mock(items=mock.Mock(return_value=[
        (('/foo/{bars}', 'PUT'), 1234),
        (('/foo/{bars}', 'GET'), 666)
    ])))
    value = extract_relevant_schema(mock_request, mock_resolver)
    assert value == 666
