# -*- coding: utf-8 -*-
"""Unit tests for tween20.py"""
from mock import Mock
import pytest

from bravado_core.operation import Operation
from bravado_core.spec import Spec
from pyramid.request import Request
from pyramid.urldispatch import Route
from pyramid_swagger.model import PathNotMatchedError

from pyramid_swagger.tween20 import get_op_for_request


def test_get_op_for_request_found():
    request = Mock(spec=Request)
    route_info = {'route': Mock(spec=Route, path='/foo/{id}')}
    expected_op = Mock(spec=Operation)
    swagger_spec = Mock(spec=Spec,
                        get_op_for_request=Mock(return_value=expected_op))
    assert expected_op == get_op_for_request(request, route_info, swagger_spec)


def test_get_op_for_request_not_found_when_route_has_no_path():
    request = Mock(spec=Request, method='GET', url='http://localhost/foo/1')
    route_info = {'route': Mock(spec=[])}
    swagger_spec = Mock(spec=Spec)
    with pytest.raises(PathNotMatchedError) as excinfo:
        get_op_for_request(request, route_info, swagger_spec)
    assert 'Could not find a matching Swagger operation' in str(excinfo.value)


def test_get_op_for_request_not_found_when_no_match_in_swagger_spec():
    request = Mock(spec=Request, method='GET', url='http://localhost/foo/1')
    route_info = {'route': Mock(spec=Route, path='/foo/{id}')}
    mock_bravado_core_get_op_for_request = Mock(return_value=None)
    swagger_spec = Mock(
        spec=Spec, get_op_for_request=mock_bravado_core_get_op_for_request)
    with pytest.raises(PathNotMatchedError) as excinfo:
        get_op_for_request(request, route_info, swagger_spec)
    assert 'Could not find a matching Swagger operation' in str(excinfo.value)
    assert mock_bravado_core_get_op_for_request.call_count == 1
