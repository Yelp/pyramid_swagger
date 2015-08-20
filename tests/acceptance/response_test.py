from contextlib import contextmanager
from _pytest.python import FixtureRequest

import mock
from mock import Mock
import pyramid.testing
from webob.multidict import MultiDict
import pyramid_swagger
import pyramid_swagger.tween
import pytest
import simplejson
from pyramid.config import Configurator
from pyramid.interfaces import IRoutesMapper
from pyramid.registry import Registry
from pyramid.response import Response
from pyramid.urldispatch import RoutesMapper
from webtest import AppError

from .request_test import test_app
from pyramid_swagger.exceptions import ResponseValidationError
from pyramid_swagger.ingest import compile_swagger_schema
from pyramid_swagger.ingest import get_resource_listing
from pyramid_swagger.tween import validation_tween_factory


class CustomResponseValidationException(Exception):
    pass


class EnhancedDummyRequest(pyramid.testing.DummyRequest):
    """
    pyramid.testing.DummyRequest doesn't support MultiDicts like the real
    pyramid.request.Request so this is the next best thing.
    """
    def __init__(self, **kw):
        super(EnhancedDummyRequest, self).__init__(**kw)
        self.GET = MultiDict(self.GET)
        # Make sure content_type attr exists is not passed in via **kw
        self.content_type = getattr(self, 'content_type', None)


@contextmanager
def validation_context(request, response=None):
    try:
        yield
    except Exception:
        raise CustomResponseValidationException


validation_ctx_path = 'tests.acceptance.response_test.validation_context'


def get_registry(settings):
    registry = Registry('testing')
    config = Configurator(registry=registry)
    if getattr(registry, 'settings', None) is None:
        config._set_settings(settings)
    registry.registerUtility(RoutesMapper(), IRoutesMapper)
    config.commit()
    return registry


def get_swagger_schema(schema_dir='tests/sample_schemas/good_app/'):
    return compile_swagger_schema(
        schema_dir,
        get_resource_listing(schema_dir, False)
    )


def _validate_against_tween(request, response=None, **overrides):
    """
    Acceptance testing helper for testing the validation tween with Swagger 1.2
    responses.

    :param request: pytest fixture
    :param response: standard fixture by default
    """
    def handler(request):
        return response or Response()

    settings = dict({
        'pyramid_swagger.swagger_versions': ['1.2'],
        'pyramid_swagger.enable_swagger_spec_validation': False,
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/'},
        **overrides
    )
    settings['pyramid_swagger.schema12'] = get_swagger_schema()
    settings['pyramid_swagger.schema20'] = None
    registry = get_registry(settings)

    # Let's make request validation a no-op so we can focus our tests.
    with mock.patch.object(pyramid_swagger.tween, 'validate_request'):
        validation_tween_factory(handler, registry)(request)


def test_response_validation_enabled_by_default():
    request = EnhancedDummyRequest(
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
    with pytest.raises(ResponseValidationError) as excinfo:
        _validate_against_tween(request, response=response)
    assert "'logging_info' is a required property" in str(excinfo.value)


def test_500_when_response_is_missing_required_field():
    request = EnhancedDummyRequest(
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
    with pytest.raises(ResponseValidationError) as excinfo:
        _validate_against_tween(request, response=response)
    assert "'logging_info' is a required property" in str(excinfo.value)


def test_200_when_response_is_void_with_none_response():
    request = EnhancedDummyRequest(
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


def test_200_when_response_is_void_with_empty_response():
    request = EnhancedDummyRequest(
        method='GET',
        path='/sample/nonstring/{int_arg}/{float_arg}/{boolean_arg}',
        params={'required_arg': 'test'},
        matchdict={'int_arg': '1', 'float_arg': '2.0', 'boolean_arg': 'true'},
    )
    response = Response(body='{}')
    _validate_against_tween(request, response=response)


def test_500_when_response_arg_is_wrong_type():
    request = EnhancedDummyRequest(
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
    with pytest.raises(ResponseValidationError) as excinfo:
        _validate_against_tween(request, response=response)
    assert "1.0 is not of type 'string'" in str(excinfo.value)


def test_500_for_bad_validated_array_response():
    request = EnhancedDummyRequest(
        method='GET',
        path='/sample_array_response',
    )
    response = Response(
        body=simplejson.dumps([{"enum_value": "bad_enum_value"}]),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(ResponseValidationError) as excinfo:
        _validate_against_tween(request, response=response)
    assert "is not one of ['good_enum_value']" in str(excinfo.value)


def test_200_for_good_validated_array_response():
    request = EnhancedDummyRequest(
        method='GET',
        path='/sample_array_response',
    )
    response = Response(
        body=simplejson.dumps([{"enum_value": "good_enum_value"}]),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )

    _validate_against_tween(request, response=response)


def test_200_for_normal_response_validation():
    app = test_app(
        request=Mock(spec=FixtureRequest, param=['1.2']),
        **{'pyramid_swagger.enable_response_validation': True}
    )
    response = app.post_json('/sample', {'foo': 'test', 'bar': 'test'})
    assert response.status_code == 200


def test_200_skip_validation_for_excluded_path():
    # FIXME(#64): This test is broken and doesn't check anything.
    app = test_app(
        request=Mock(spec=FixtureRequest, param=['1.2']),
        **{'pyramid_swagger.exclude_paths': [r'^/sample/?']}
    )
    response = app.get(
        '/sample/path_arg1/resource',
        params={'required_arg': 'test'}
    )
    assert response.status_code == 200


def test_app_error_if_path_not_in_spec_and_path_validation_disabled():
    """If path missing and validation is disabled we want to let something else
    handle the error. TestApp throws an AppError, but Pyramid would throw a
    HTTPNotFound exception.
    """
    with pytest.raises(AppError):
        app = test_app(
            request=Mock(spec=FixtureRequest, param=['1.2']),
            **{'pyramid_swagger.enable_path_validation': False}
        )
        assert app.get('/this/path/doesnt/exist')


def test_response_validation_context():
    request = EnhancedDummyRequest(
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
    with pytest.raises(CustomResponseValidationException):
        _validate_against_tween(
            request,
            response=response,
            **{'pyramid_swagger.validation_context_path': validation_ctx_path}
        )
