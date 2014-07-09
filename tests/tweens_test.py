# -*- coding: utf-8 -*-
"""Unit tests for tweens.py"""
import mock
import re
import pyramid.testing
import pytest
import simplejson
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.response import Response


from pyramid_swagger import tween
from pyramid_swagger.tween import prepare_body
from pyramid_swagger.tween import validate_outgoing_response
from pyramid_swagger.tween import validation_tween_factory


def test_response_charset_missing_raises_5xx():
    with pytest.raises(HTTPInternalServerError):
        prepare_body(
            Response(content_type='foo')
        )


def test_unconfigured_schema_dir_raises_error():
    """If we send a settings dict without schema_dir, fail fast."""
    with pytest.raises(ValueError):
        validation_tween_factory(
            mock.ANY,
            mock.Mock(settings={})
        )


def test_validation_skips_path_properly():
    skip_res = [re.compile(r) for r in tween.SKIP_VALIDATION_DEFAULT]
    assert any([s.match('/static') for s in skip_res])
    assert any([s.match('/static/foobar') for s in skip_res])

    assert not any([s.match('/sample') for s in skip_res])


# TODO: Should probably be migrated to acceptance tests after we make mocking
# schemas easier there.
def test_validation_content_type_with_json():
    fake_schema = mock.Mock(response_body_schema={'type': 'object'})
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/status',
    )
    response = Response(
        body=simplejson.dumps({'status': 'good'}),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    validate_outgoing_response(request, response, fake_schema, None)


def test_raw_string():
    fake_schema = mock.Mock(response_body_schema={'type': 'string'})
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/status/version',
    )
    response = Response(
        body='abe1351f',
        headers={'Content-Type': 'application/text; charset=UTF-8'},
    )
    validate_outgoing_response(request, response, fake_schema, None)
