# -*- coding: utf-8 -*-
"""Unit tests for tweens.py"""
import mock
import re
import pytest
import simplejson
from mock import Mock
from pyramid.response import Response


from pyramid_swagger.exceptions import ResponseValidationError
from pyramid_swagger.tween import DEFAULT_EXCLUDED_PATHS
from pyramid_swagger.tween import get_exclude_paths
from pyramid_swagger.tween import prepare_body
from pyramid_swagger.tween import should_exclude_path
from pyramid_swagger.tween import should_exclude_route
from pyramid_swagger.tween import validate_response


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


def test_response_charset_missing_raises_5xx():
    with pytest.raises(ResponseValidationError):
        prepare_body(
            Response(content_type='foo')
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


# TODO: Should probably be migrated to acceptance tests after we make mocking
# schemas easier there.
def test_validation_content_type_with_json():
    fake_schema = mock.Mock(response_body_schema={'type': 'object'})
    fake_validator = mock.Mock(schema=fake_schema)
    body = {'status': 'good'}
    response = Response(
        body=simplejson.dumps(body),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    validate_response(response, fake_validator)
    fake_validator.validate.assert_called_once_with(body)


def test_raw_string():
    fake_schema = mock.Mock(response_body_schema={'type': 'string'})
    fake_validator = mock.Mock(schema=fake_schema)
    response = Response(
        body='abe1351f',
        headers={'Content-Type': 'application/text; charset=UTF-8'},
    )
    validate_response(response, fake_validator)
    fake_validator.validate.assert_called_once_with(
        response.body.decode('utf-8'))
