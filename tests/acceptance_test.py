import pytest
import pyramid_swagger
import mock
import simplejson
from pyramid.httpexceptions import HTTPClientError
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.config import Configurator
from pyramid_swagger.tween import validation_tween_factory
from pyramid.registry import Registry
from pyramid.response import Response
import pyramid.testing


def get_registry(settings):
    registry = Registry('testing')
    config = Configurator(registry=registry)
    if getattr(registry, 'settings', None) is None:
        config._set_settings(settings)
    config.commit()
    return registry


def _validate_against_tween(request, response=None, settings=None):
    """
    Acceptance testing helper for testing the validation tween.

    :param request: pytest fixture
    :param response: standard fixture by default
    """
    def handler(request):
        return response or Response()
    settings = settings or dict({
        'pyramid_swagger.schema_path': 'tests/sample_swagger_spec.json',
        'pyramid_swagger.enable_response_validation': False,
    })
    registry = get_registry(settings=settings)
    validation_tween_factory(handler, registry)(request)


def test_400_if_required_query_args_absent():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={},
        matchdict={'path_arg': 'path_arg1'},
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_200_if_optional_query_args_absent():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},  # no `optional_arg` arg
        matchdict={'path_arg': 'path_arg1'},
    )
    _validate_against_tween(request)


def test_400_if_request_arg_is_wrong_type():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 1.0},
        matchdict={'path_arg': 'path_arg1'},
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_400_if_path_not_in_swagger():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/does_not_exist',
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_400_if_path_arg_is_wrong_type():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/invalid_arg/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'invalid_arg'},
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_400_if_required_body_is_missing():
    request = pyramid.testing.DummyRequest(
        method='POST',
        path='/sample_post',
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_400_if_body_has_missing_required_arg():
    request = pyramid.testing.DummyRequest(
        method='POST',
        path='/sample_post',
        json_body={'bar': 'test'},
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_200_if_body_has_missing_optional_arg():
    request = pyramid.testing.DummyRequest(
        method='POST',
        path='/sample_post',
        json_body={'foo': 'test'},
    )
    _validate_against_tween(request)


def test_200_if_required_body_is_model():
    request = pyramid.testing.DummyRequest(
        method='POST',
        path='/sample_post',
        json_body={'foo': 'test', 'bar': 'test'},
    )
    _validate_against_tween(request)


def test_200_if_required_body_is_primitives():
    request = pyramid.testing.DummyRequest(
        method='POST',
        path='/post_with_primitive_body',
        json_body=["foo", "bar"],
    )
    _validate_against_tween(request)


def test_response_validation_disabled_by_default():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )
    # Omit the logging_info key from the response. If response validation
    # occurs, we'll fail it.
    response = mock.Mock(
        content=simplejson.dumps({'raw_response': 'foo'}),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    settings = {
        'pyramid_swagger.schema_path': 'tests/sample_swagger_spec.json',
    }
    _validate_against_tween(request, response=response, settings=settings)


def test_500_when_response_is_missing_required_field():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )
    settings = {
        'pyramid_swagger.schema_path': 'tests/sample_swagger_spec.json',
        'pyramid_swagger.enable_response_validation': True,
    }
    # Omit the logging_info key from the response.
    response = mock.Mock(
        content=simplejson.dumps({'raw_response': 'foo'}),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response, settings=settings)


def test_500_when_response_arg_is_wrong_type():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )
    data = {
        'raw_response': 1.0,
        'logging_info': {'foo': 'bar'}
    }
    settings = {
        'pyramid_swagger.schema_path': 'tests/sample_swagger_spec.json',
        'pyramid_swagger.enable_response_validation': True,
    }
    response = mock.Mock(
        content=simplejson.dumps(data),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response, settings=settings)


def test_response_validation_success():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )
    data = {
        'raw_response': 'foo',
        'logging_info': {'foo': 'bar'}
    }
    settings = {
        'pyramid_swagger.schema_path': 'tests/sample_swagger_spec.json',
        'pyramid_swagger.enable_response_validation': True,
    }
    response = mock.Mock(
        content=simplejson.dumps(data),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    _validate_against_tween(request, response=response, settings=settings)


def test_pyramid_swagger_import():
    registry = Registry('testing')
    config = Configurator(registry=registry)
    pyramid_swagger.includeme(config)
