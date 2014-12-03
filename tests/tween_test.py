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
from pyramid_swagger.tween import load_settings
from pyramid_swagger.tween import prepare_body
from pyramid_swagger.tween import should_exclude_path
from pyramid_swagger.tween import validate_outgoing_response


def test_default_exclude_paths():
    assert get_exclude_paths(Mock(settings={})) \
        == [re.compile(r) for r in DEFAULT_EXCLUDED_PATHS]


def test_exclude_path_with_string():
    path_string = r'/foo/'
    assert get_exclude_paths(
        Mock(settings={'pyramid_swagger.exclude_paths': path_string})) \
        == [re.compile(r) for r in [path_string]]


def test_exclude_path_with_overrides():
    paths = [r'/foo/', r'/bar/']
    assert get_exclude_paths(
        Mock(settings={'pyramid_swagger.exclude_paths': paths})) \
        == [re.compile(r) for r in paths]


def test_exclude_path_with_old_setting():
    # TODO(#63): remove deprecated `skip_validation` setting in v2.0.
    paths = [r'/foo/', r'/bar/']
    assert get_exclude_paths(
        Mock(settings={'pyramid_swagger.skip_validation': paths})) \
        == [re.compile(r) for r in paths]


def test_response_charset_missing_raises_5xx():
    with pytest.raises(ResponseValidationError):
        prepare_body(
            Response(content_type='foo')
        )


def test_unconfigured_schema_dir_uses_api_docs():
    """If we send a settings dict without schema_dir, fail fast."""
    assert load_settings(mock.Mock(settings={}))[0] == 'api_docs/'


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
    response = Response(
        body=simplejson.dumps({'status': 'good'}),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    validate_outgoing_response(response, fake_schema, None)


def test_raw_string():
    fake_schema = mock.Mock(response_body_schema={'type': 'string'})
    response = Response(
        body='abe1351f',
        headers={'Content-Type': 'application/text; charset=UTF-8'},
    )
    validate_outgoing_response(response, fake_schema, None)
