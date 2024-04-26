# -*- coding: utf-8 -*-
"""Unit tests for tweens.py"""
from __future__ import absolute_import

import re

import mock
import pytest
from bravado_core.exception import SwaggerMappingError
from bravado_core.operation import Operation
from bravado_core.spec import Spec
from mock import Mock
from pyramid.request import Request
from pyramid.response import Response
from pyramid.urldispatch import Route

from pyramid_swagger.exceptions import RequestValidationError
from pyramid_swagger.model import PathNotMatchedError
from pyramid_swagger.tween import DEFAULT_EXCLUDED_PATHS
from pyramid_swagger.tween import get_exclude_paths
from pyramid_swagger.tween import get_op_for_request
from pyramid_swagger.tween import get_swagger_objects
from pyramid_swagger.tween import get_swagger_versions
from pyramid_swagger.tween import PyramidSwaggerRequest
from pyramid_swagger.tween import PyramidSwaggerResponse
from pyramid_swagger.tween import Settings
from pyramid_swagger.tween import should_exclude_path
from pyramid_swagger.tween import should_exclude_route
from pyramid_swagger.tween import SWAGGER_20
from pyramid_swagger.tween import validation_error
# from pyramid_swagger.tween import validate_response


def assert_eq_regex_lists(left, right):
    assert [r.pattern for r in left] == [r.pattern for r in right]


def test_default_exclude_paths():
    assert_eq_regex_lists(
        get_exclude_paths(Mock(settings={})),
        [re.compile(r) for r in DEFAULT_EXCLUDED_PATHS]
    )


def test_exclude_path_with_string():
    path_string = r'/foo/'
    registry = Mock(settings={'pyramid_swagger.exclude_paths': path_string})
    assert_eq_regex_lists(
        get_exclude_paths(registry),
        [re.compile(r) for r in [path_string]]
    )


def test_exclude_path_with_overrides():
    paths = [r'/foo/', r'/bar/']
    compiled = get_exclude_paths(
        Mock(settings={'pyramid_swagger.exclude_paths': paths}))
    assert_eq_regex_lists(
        compiled,
        [re.compile(r) for r in paths]
    )


def test_exclude_path_with_old_setting():
    # TODO(#63): remove deprecated `skip_validation` setting in v2.0.
    paths = [r'/foo/', r'/bar/']
    assert_eq_regex_lists(
        get_exclude_paths(
            Mock(settings={'pyramid_swagger.skip_validation': paths})),
        [re.compile(r) for r in paths]
    )


@pytest.fixture
def mock_route_info():
    class MockRoute(object):
        name = 'route-one'

    return {'route': MockRoute}


def test_should_exclude_route(mock_route_info):
    assert should_exclude_route(set(['route-one', 'two']), mock_route_info)


def test_should_exclude_route_no_matched_route(mock_route_info):
    assert not should_exclude_route(set(['foo', 'two']), mock_route_info)


def test_should_exclude_route_no_route():
    assert not should_exclude_route(set(['foo', 'two']), {'route': None})


def test_validation_skips_path_properly():
    excluded_paths = [re.compile(r) for r in DEFAULT_EXCLUDED_PATHS]
    assert should_exclude_path(excluded_paths, '/static')
    assert should_exclude_path(excluded_paths, '/static/foobar')
    assert should_exclude_path(excluded_paths, '/api-docs')
    assert should_exclude_path(excluded_paths, '/api-docs/foobar')

    assert not should_exclude_path(excluded_paths, '/sample')
    assert not should_exclude_path(excluded_paths, '/sample/resources')


def build_mock_validator(properties):
    return mock.Mock(
        spec=['schema', 'validate'],
        schema={
            'properties': dict(
                (name, {'type': type_})
                for name, type_ in properties.items()
            )
        },
    )


def test_get_op_for_request_found():
    request = Mock(spec=Request)
    route_info = {'route': Mock(spec=Route, path='/foo/{id}')}
    expected_op = Mock(spec=Operation)
    swagger_spec = Mock(spec=Spec,
                        get_op_for_request=Mock(return_value=expected_op))
    assert expected_op == get_op_for_request(request, route_info, swagger_spec)


def test_get_op_for_request_not_found_route_not_registered():
    request = Mock(spec=Request, method='GET', url='http://localhost/foo/1')
    route_info = {'route': Mock(spec=[])}
    swagger_spec = Mock(spec=Spec)
    with pytest.raises(PathNotMatchedError) as excinfo:
        get_op_for_request(request, route_info, swagger_spec)
    assert 'Could not find a matching route' in str(excinfo.value)


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


def test_get_swagger_versions_success():
    settings = {'pyramid_swagger.swagger_versions': ['2.0']}
    assert set(['2.0']) == get_swagger_versions(settings)


def test_get_swagger_versions_empty():
    settings = {'pyramid_swagger.swagger_versions': []}
    with pytest.raises(ValueError) as excinfo:
        get_swagger_versions(settings)
    assert 'pyramid_swagger.swagger_versions is empty' in str(excinfo.value)


def test_get_swagger_versions_unsupported():
    settings = {'pyramid_swagger.swagger_versions': ['10.0', '2.0']}
    with pytest.raises(ValueError) as excinfo:
        get_swagger_versions(settings)
    assert 'Swagger version 10.0 is not supported' in str(excinfo.value)


def test_validaton_error_decorator_transforms_SwaggerMappingError():

    @validation_error(RequestValidationError)
    def foo():
        raise SwaggerMappingError('kaboom')

    with pytest.raises(RequestValidationError) as excinfo:
        foo()
    assert 'kaboom' in str(excinfo.value)


def test_validation_error_includes_child():

    @validation_error(RequestValidationError)
    def foo():
        raise SwaggerMappingError('kaboom')

    try:
        foo()
    except RequestValidationError as e:
        assert isinstance(e.child, SwaggerMappingError)
        assert 'kaboom' in str(e)


@pytest.fixture
def registry():
    config = {
        'pyramid_swagger.schema12': None,
        'pyramid_swagger.schema20': None,
    }
    return Mock(settings=config)


@pytest.fixture
def settings():
    return Mock(spec=Settings)


def test_get_swagger20_objects_if_only_swagger20_version_is_present(
        settings, registry):
    registry.settings['pyramid_swagger.swagger_versions'] = [SWAGGER_20]
    registry.settings['pyramid_swagger.schema20'] = 'schema20'
    swagger_handler, spec = get_swagger_objects(settings, registry)
    assert 'swagger20_handler' in str(swagger_handler)
    assert 'schema20' == spec


def test_is_swagger_documentation_route_without_route_is_safe():
    """
    Not sure if `None` is an option for the `route_info` dict, but make
    sure nothing crashes in that possible scenario.
    """
    from pyramid_swagger.tween import is_swagger_documentation_route
    assert is_swagger_documentation_route(None) is False


def test_request_properties():
    root_request = Request({}, headers={"X-Some-Special-Header": "foobar"})
    # this is a slightly baroque mechanism to make sure that the request is
    # internally consistent for all test environments
    root_request.body = '{"myKey": 42}'.encode()
    assert '{"myKey": 42}' == root_request.text
    request = PyramidSwaggerRequest(root_request, {})
    assert {"myKey": 42} == request.body
    assert "foobar" == request.headers["X-Some-Special-Header"]


def test_response_properties():
    root_response = Response(
        headers={"X-Some-Special-Header": "foobar"},
        body=b'{"myKey": 42}'
    )
    # these must be set for the "text" attribute of webob.Response to be
    # readable, and setting them in the constructor gets into a conflict
    # with the custom header argument
    root_response.content_type = "application/json"
    root_response.charset = 'utf8'
    response = PyramidSwaggerResponse(root_response)
    assert '{"myKey": 42}' == response.text
    assert b'{"myKey": 42}' == response.raw_bytes
    assert "foobar" == response.headers["X-Some-Special-Header"]
    assert 'application/json' == response.content_type


def test_empty_response_properties():
    root_response = Response(headers={"X-Some-Special-Header": "foobar"})
    response = PyramidSwaggerResponse(root_response)
    assert response.text is None
    assert "foobar" == response.headers["X-Some-Special-Header"]
    assert response.content_type is None
