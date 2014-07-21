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
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    })
    registry = get_registry(settings=settings)
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
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response, settings=settings)


def test_500_when_response_is_missing_required_field():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    # Omit the logging_info key from the response.
    response = Response(
        body=simplejson.dumps({'raw_response': 'foo'}),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response, settings=settings)


def test_200_when_response_is_void():
    request = pyramid.testing.DummyRequest(
        method='GET',
        path='/sample/nonstring/{int_arg}/{float_arg}/{boolean_arg}',
        params={'required_arg': 'test'},
        matchdict={'int_arg': '1', 'float_arg': '2.0', 'boolean_arg': 'true'},
    )
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    response = Response(
        body=simplejson.dumps(None),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
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
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    response = Response(
        body=simplejson.dumps(data),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(HTTPInternalServerError):
        _validate_against_tween(request, response=response, settings=settings)


def test_200_for_normal_response_validation():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
        'pyramid_swagger.enable_response_validation': True,
    }
    test_app(settings).post_json(
        '/sample',
        {'foo': 'test', 'bar': 'test'},
        status=200
    )


def test_200_skip_validation_with_wrong_response():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.skip_validation': '/(sample)\\b',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    test_app(settings).get(
        '/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        status=200
    )
