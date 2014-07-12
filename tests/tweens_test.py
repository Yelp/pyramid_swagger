# -*- coding: utf-8 -*-
"""Unit tests for tweens.py"""
import mock
import re
import pytest
import simplejson
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.response import Response


from pyramid_swagger import tween
from pyramid_swagger.tween import load_settings
from pyramid_swagger.tween import prepare_body
from pyramid_swagger.tween import should_skip_validation
from pyramid_swagger.tween import validate_outgoing_response


def test_response_charset_missing_raises_5xx():
    with pytest.raises(HTTPInternalServerError):
        prepare_body(
            Response(content_type='foo')
        )


def test_unconfigured_schema_dir_uses_swagger_schemas():
    """If we send a settings dict without schema_dir, fail fast."""
    assert load_settings(mock.Mock(settings={}))[0] == 'swagger_schemas/'


def test_validation_skips_path_properly():
    skip_res = [re.compile(r) for r in tween.SKIP_VALIDATION_DEFAULT]
    assert should_skip_validation(skip_res, '/static')
    assert should_skip_validation(skip_res, '/static/foobar')
    assert should_skip_validation(skip_res, '/api-docs')
    assert should_skip_validation(skip_res, '/api-docs/foobar')

    assert not should_skip_validation(skip_res, '/sample')
    assert not should_skip_validation(skip_res, '/sample/resources')


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
