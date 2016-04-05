#
# Swagger 2.0 response acceptance tests
#
# Based on request_test.py (Swagger 1.2 tests). Differences made it hard for
# a single codebase to exercise both Swagger 1.2 and 2.0 responses.
#
from _pytest.python import FixtureRequest
from mock import patch, Mock
from pyramid.interfaces import IRoutesMapper
from pyramid.response import Response
import pytest
import simplejson
from webtest.app import AppError

from .request_test import test_app
from pyramid_swagger.exceptions import ResponseValidationError
from pyramid_swagger.ingest import get_swagger_spec
from pyramid_swagger.tween import validation_tween_factory
from tests.acceptance.response_test import validation_ctx_path, \
    EnhancedDummyRequest, get_registry
from tests.acceptance.response_test import CustomResponseValidationException


def _validate_against_tween(request, response=None, path_pattern='/',
                            **overrides):
    """
    Acceptance testing helper for testing the swagger tween with Swagger 2.0
    responses.

    :param request: pyramid request
    :param response: standard fixture by default
    :param path_pattern: Path pattern eg. /foo/{bar}
    :param overrides: dict of overrides for `pyramid_swagger` config
    """
    def handler(request):
        return response or Response()

    settings = dict({
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
        'pyramid_swagger.enable_response_validation': True,
        'pyramid_swagger.swagger_versions': ['2.0']},
        **overrides
    )

    spec = get_swagger_spec(settings)
    settings['pyramid_swagger.schema12'] = None
    settings['pyramid_swagger.schema20'] = spec

    registry = get_registry(settings)

    # This is a little messy because the current flow of execution doesn't
    # set up the route_info in pyramid. Have to mock out the `route_info`
    # so that usages in the tween meet expectations. Holler if you know a
    # better way to do this!
    op = spec.get_op_for_request(request.method, path_pattern)
    mock_route_info = {'match': request.matchdict, 'route': None}
    mock_route_mapper = Mock(spec=IRoutesMapper, return_value=mock_route_info)
    with patch('pyramid_swagger.tween.get_op_for_request', return_value=op):
        with patch('pyramid.registry.Registry.queryUtility',
                   return_value=mock_route_mapper):
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
    with pytest.raises(ResponseValidationError):
        _validate_against_tween(
            request,
            response=response,
            path_pattern='/sample/{path_arg}/resource')


def test_500_when_response_is_missing_required_field():

    request = EnhancedDummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )

    # Omit the logging_info key from the response to induce failure
    response = Response(
        body=simplejson.dumps({'raw_response': 'foo'}),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )

    with pytest.raises(ResponseValidationError) as excinfo:
        _validate_against_tween(
            request,
            response=response,
            path_pattern='/sample/{path_arg}/resource')

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
    _validate_against_tween(
        request,
        response=response,
        path_pattern='/sample/nonstring/{int_arg}/{float_arg}/{boolean_arg}')


def test_200_when_response_is_void_with_empty_response():
    request = EnhancedDummyRequest(
        method='GET',
        path='/sample/nonstring/{int_arg}/{float_arg}/{boolean_arg}',
        params={'required_arg': 'test'},
        matchdict={'int_arg': '1', 'float_arg': '2.0', 'boolean_arg': 'true'},
    )
    response = Response(body='{}')
    _validate_against_tween(
        request,
        response=response,
        path_pattern='/sample/nonstring/{int_arg}/{float_arg}/{boolean_arg}')


def test_500_when_response_arg_is_wrong_type():
    request = EnhancedDummyRequest(
        method='GET',
        path='/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        matchdict={'path_arg': 'path_arg1'},
    )
    response = Response(
        body=simplejson.dumps({
            'raw_response': 1.0,  # <-- is supposed to be a string
            'logging_info': {'foo': 'bar'}
        }),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    with pytest.raises(ResponseValidationError) as excinfo:
        _validate_against_tween(
            request,
            response=response,
            path_pattern='/sample/{path_arg}/resource')

    assert "1.0 is not of type " in str(excinfo.value)


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
        _validate_against_tween(
            request,
            response=response,
            path_pattern='/sample_array_response')

    assert "'bad_enum_value' is not one of " in \
           str(excinfo.value)


def test_200_for_good_validated_array_response():
    request = EnhancedDummyRequest(
        method='GET',
        path='/sample_array_response',
    )
    response = Response(
        body=simplejson.dumps([{"enum_value": "good_enum_value"}]),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )

    _validate_against_tween(
        request,
        response=response,
        path_pattern='/sample_array_response')


def test_200_for_normal_response_validation():
    assert test_app(
        request=Mock(spec=FixtureRequest, param=['2.0']),
        **{'pyramid_swagger.enable_response_validation': True}) \
        .post_json('/sample', {'foo': 'test', 'bar': 'test'}) \
        .status_code == 200


def test_app_error_if_path_not_in_spec_and_path_validation_disabled():
    """If path missing and validation is disabled we want to let something else
    handle the error. TestApp throws an AppError, but Pyramid would throw a
    HTTPNotFound exception.
    """
    with pytest.raises(AppError):
        assert test_app(
            request=Mock(spec=FixtureRequest, param=['2.0']),
            **{'pyramid_swagger.enable_path_validation': False}) \
            .get('/this/path/doesnt/exist')


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
            path_pattern='/sample/{path_arg}/resource',
            **{'pyramid_swagger.validation_context_path': validation_ctx_path}
        )
