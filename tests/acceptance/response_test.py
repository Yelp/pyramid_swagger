import mock
import pyramid.testing
import pyramid_swagger
import pyramid_swagger.tween
import pytest
import simplejson
from .request_test import test_app
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.registry import Registry
from pyramid.response import Response
from pyramid_swagger.tween import validation_tween_factory
from webtest import AppError


def get_registry(settings):
    registry = Registry('testing')
    config = Configurator(registry=registry)
    if getattr(registry, 'settings', None) is None:
        config._set_settings(settings)
    config.commit()
    return registry


def _validate_against_tween(request, response=None, **overrides):
    """
    Acceptance testing helper for testing the validation tween.

    :param request: pytest fixture
    :param response: standard fixture by default
    """
    def handler(request):
        return response or Response()

    settings = dict({
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False},
        **overrides
    )

    registry = get_registry(settings)

    # Let's make request validation a no-op so we can focus our tests.
    with mock.patch.object(pyramid_swagger.tween, '_validate_request'):
        validation_tween_factory(handler, registry)(request)


def test_response_validation_enabled_by_default():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )
    # Omit the logging_info key from the response. If response validation
    # occurs, we'll fail it.
    response = Response(
        body=simplejson.dumps({'raw_response': 'foo'}),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response)


def test_500_when_response_is_missing_required_field():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )
    # Omit the logging_info key from the response.
    response = Response(
        body=simplejson.dumps({'raw_response': 'foo'}),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response)


def test_200_when_response_is_void():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/nonstring/{int_arg}/{float_arg}/{boolean_arg}',
        params={'required_arg': 'test'},
        matchdict={'int_arg': '1', 'float_arg': '2.0', 'boolean_arg': 'true'},
    )
    response = Response(
        body=simplejson.dumps(None),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    _validate_against_tween(request, response=response)


def test_500_when_response_arg_is_wrong_type():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )
    response = Response(
        body=simplejson.dumps({
            'raw_response': 1.0,
            'logging_info': {'foo': 'bar'}
        }),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response)


def test_500_for_bad_validated_array_response():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample_array_response',
    )
    response = Response(
        body=simplejson.dumps([{"enum_value": "bad_enum_value"}]),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response)


def test_200_for_good_validated_array_response():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample_array_response',
    )
    response = Response(
        body=simplejson.dumps([{"enum_value": "good_enum_value"}]),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )

    _validate_against_tween(request, response=response)


def test_200_for_normal_response_validation():
    assert test_app(**{'pyramid_swagger.enable_response_validation': True}) \
        .post_json('/sample', {'foo': 'test', 'bar': 'test'}) \
        .status_code == 200


def test_200_skip_validation_with_wrong_response():
    assert test_app(**{'pyramid_swagger.skip_validation': ['/(sample)\\b']}) \
        .get('/sample/path_arg1/resource', params={'required_arg': 'test'}) \
        .status_code == 200


def test_app_error_if_path_not_in_spec_and_path_validation_disabled():
    """If path missing and validation is disabled we want to let something else
    handle the error. TestApp throws an AppError, but Pyramid would throw a
    HTTPNotFound exception.
    """
    with pytest.raises(AppError):
        assert test_app(**{'pyramid_swagger.enable_path_validation': False}) \
            .get('/this/path/doesnt/exist')
