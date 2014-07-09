# -*- coding: utf-8 -*-
"""
Tests that our validation tween (and helpers) is working successfully.

The tests here all use the sample swagger spec stored in swagger.json at the
root of this package.
"""
import mock
from pyramid.response import Response
import pyramid.testing
import re
import simplejson
from pyramid_swagger import tween
from pyramid_swagger.tween import validate_outgoing_response


def test_validation_skips_path_properly():
    expresion = re.compile(tween.SKIP_VALIDATION_DEFAULT[0])
    assert expresion.match('/static')
    assert expresion.match('/static/foobar')
    assert not expresion.match('/staticgeo')

    assert not expresion.match('/v1/reverse-many')
    assert not expresion.match(
        '/geocoder/bing/forward_unstructured'
    )


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
