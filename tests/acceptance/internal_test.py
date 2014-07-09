import pytest
import jsonschema.exceptions
import pyramid_swagger
import pyramid_swagger.tween
import simplejson
import mock
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


def test_pyramid_swagger_import():
    registry = Registry('testing')
    config = Configurator(registry=registry)
    pyramid_swagger.includeme(config)


def test_bad_schema_validated_on_tween_creation_by_default():
    settings = {
        'pyramid_swagger.schema_directory':
            'tests/sample_schemas/bad_app/',
    }
    registry = get_registry(settings=settings)
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validation_tween_factory(mock.ANY, registry)


def test_bad_schema_not_validated_if_spec_validation_is_disabled():
    settings = {
        'pyramid_swagger.schema_directory':
            'tests/sample_schemas/bad_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    registry = get_registry(settings=settings)
    validation_tween_factory(mock.ANY, registry)
