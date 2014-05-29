# -*- coding: utf-8 -*-
"""
Tests that our validation tween (and helpers) is working successfully.

The tests here all use the sample swagger spec stored in swagger.json at the
root of this package.
"""
import mock
import pyramid.testing
import pytest
import simplejson
from pyramid.config import Configurator
from pyramid.registry import Registry
from pyramid.response import Response

from pyramid_swagger import tweens
from pyramid_swagger.load_schema import load_schema
from pyramid_swagger.tweens import partial_path_match
from pyramid.httpexceptions import HTTPClientError
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid_swagger.tweens import validate_outgoing_response
from pyramid_swagger.tweens import validation_tween_factory


schema_resolver = load_schema('tests/sample_swagger_spec.json')


@pytest.fixture()
def request():
    query = '140 new montgomery, sf, ca'
    return pyramid.testing.DummyRequest(
        method='GET',
        path='/geocoder/bing/forward_unstructured',
        params={'query': query, 'locale': 'en_US'}
    )


@pytest.fixture()
def response():
    """Sample (valid) request and response data for validation testing."""
    data = {
        'raw_response': 'foo',
        'logging_info': {'foo': 'bar'}
    }
    return mock.Mock(
        content=simplejson.dumps(data),
        headers={'header1': 'application/json; charset=UTF-8'},
    )


def get_registry(settings=None):
    if settings is None:
        settings = {}
    registry = Registry('testing')
    config = Configurator(registry=registry)
    if getattr(registry, 'settings', None) is None:
        config._set_settings(settings)
    config.commit()
    return registry


def _validate_against_tween(request, response=None, settings=None):
    def handler(request):
        return response or Response()
    settings = settings or {
        'pyramid_swagger.schema_path': 'tests/sample_swagger_spec.json',
        'pyramid_swagger.enable_response_validation': True,
    }
    registry = get_registry(settings=settings)
    validation_tween_factory(handler, registry)(request)


def test_validation_fails_for_missing_query_arg(request):
    request.params = {'query': 'SF'}  # No locale
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_validation_fails_for_missing_body():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/required_body',
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_validation_fails_for_mistyped_arg(request):
    request.params = {'query': 'SF', 'locale': 1.0}
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_response_validation_disabled_by_default(request, response):
    # Omit the logging_info key from the response. If response validation
    # occurs, we'll fail it.
    response.content = simplejson.dumps({'raw_response': 'foo'})
    settings = {
        'pyramid_swagger.schema_path': 'tests/sample_swagger_spec.json',
    }
    _validate_against_tween(request, response=response, settings=settings)


def test_validation_fails_when_response_is_wrong(request, response):
    # Omit the logging_info key from the response.
    response.content = simplejson.dumps({'raw_response': 'foo'})
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response)


def test_response_validation_fails_with_wrong_type(request, response):
    data = {
        'raw_response': 1.0,
        'logging_info': {'foo': 'bar'}
    }
    response.content = simplejson.dumps(data)
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response)


def test_response_validation_success(request, response):
    _validate_against_tween(request, response=response)


def test_validation_skips_path_properly():
    assert tweens.skip_validation_re.match('/static')
    assert tweens.skip_validation_re.match('/static/foobar')
    assert not tweens.skip_validation_re.match('/staticgeo')

    assert not tweens.skip_validation_re.match('/v1/reverse-many')
    assert not tweens.skip_validation_re.match(
        '/geocoder/bing/forward_unstructured'
    )


def test_nonexistant_path_returns_4xx_error():
    request.method = 'GET'
    request.path = '/madeuppath'
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


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
