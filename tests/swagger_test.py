# -*- coding: utf-8 -*-
"""
Tests that our validation tween (and helpers) is working successfully.

The tests here all use the sample swagger spec stored in swagger.json at the
root of this package.
"""
import mock
import pyramid.testing
import simplejson
from pyramid_swagger import tween
from pyramid_swagger.tween import partial_path_match
from pyramid_swagger.tween import validate_outgoing_response


def test_validation_skips_path_properly():
    assert tween.skip_validation_re.match('/static')
    assert tween.skip_validation_re.match('/static/foobar')
    assert not tween.skip_validation_re.match('/staticgeo')

    assert not tween.skip_validation_re.match('/v1/reverse-many')
    assert not tween.skip_validation_re.match(
        '/geocoder/bing/forward_unstructured'
    )


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


# TODO: Should probably be migrated to acceptance tests after we make mocking
# schemas easier there.
def test_validation_content_type_with_json():
    fake_schema = mock.Mock(response_body_schema={'type': 'object'})
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/status',
    )
    response = mock.Mock(
        content=simplejson.dumps({'status': 'good'}),
        headers={'header1': 'application/json; charset=UTF-8'},
    )
    validate_outgoing_response(request, response, fake_schema, None)


def test_raw_string():
    fake_schema = mock.Mock(response_body_schema={'type': 'string'})
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/status/version',
    )
    response = mock.Mock(
        content='abe1351f',
        headers={'header1': 'application/text; charset=UTF-8'},
    )
    validate_outgoing_response(request, response, fake_schema, None)
