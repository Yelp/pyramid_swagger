import pytest
import mock
import simplejson
from pyramid.httpexceptions import HTTPClientError
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.config import Configurator
from pyramid_swagger.tween import validation_tween_factory
from pyramid.registry import Registry
from pyramid.response import Response
import pyramid.testing


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
        path='/geocoder/bing/forward_unstructured',
        params={'query': 'sf, ca'}  # No locale
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_200_if_optional_query_args_absent():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/geocoder/bing/forward_unstructured',
        params={'query': 'sf, ca', 'locale': 'en_US'}  # No from_country
    )
    _validate_against_tween(request)


@pytest.mark.xfail(reason='github.com/striglia/pyramid_swagger/issues/11')
def test_400_if_request_arg_is_wrong_type():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/geocoder/bing/forward_unstructured',
        params={'query': '1.0', 'locale': 'en_US'}
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


@pytest.mark.xfail(reason='github.com/striglia/pyramid_swagger/issues/13')
def test_400_if_path_arg_is_wrong_type():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/geocoder/invalid_arg/forward_unstructured',
        params={'query': 'sf, ca', 'locale': 'en_US'}
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_400_if_required_body_is_missing():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/required_body',
    )
    with pytest.raises(HTTPClientError):
        _validate_against_tween(request)


def test_200_if_required_body_is_present():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/required_body',
        body=simplejson.dumps([[1, 2]]),
        json_body=[[1, 2]],
    )
    _validate_against_tween(request)


@pytest.mark.xfail(reason='new test still buggy')
def test_200_if_optional_body_is_missing():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/optional_body',
    )
    _validate_against_tween(request)


def test_response_validation_disabled_by_default():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/geocoder/bing/forward_unstructured',
        params={'query': 'sf, ca', 'locale': 'en_US'}
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
        path='/geocoder/bing/forward_unstructured',
        params={'query': 'sf, ca', 'locale': 'en_US'}
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
        path='/geocoder/bing/forward_unstructured',
        params={'query': 'sf, ca', 'locale': 'en_US'}
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
        path='/geocoder/bing/forward_unstructured',
        params={'query': 'sf, ca', 'locale': 'en_US'}
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
