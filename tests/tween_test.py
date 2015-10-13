# -*- coding: utf-8 -*-
"""Unit tests for tweens.py"""
import re

from bravado_core.exception import SwaggerMappingError
from bravado_core.operation import Operation
from bravado_core.spec import Spec
import mock
from mock import Mock
from pyramid.request import Request
from pyramid.response import Response
from pyramid.urldispatch import Route
import pytest
import simplejson

from pyramid_swagger.exceptions import ResponseValidationError
from pyramid_swagger.exceptions import RequestValidationError
from pyramid_swagger.load_schema import ValidatorMap, SchemaValidator
from pyramid_swagger.model import PathNotMatchedError
from pyramid_swagger.tween import DEFAULT_EXCLUDED_PATHS, get_op_for_request, \
    validation_error
from pyramid_swagger.tween import PyramidSwaggerRequest
from pyramid_swagger.tween import get_exclude_paths
from pyramid_swagger.tween import get_swagger_objects
from pyramid_swagger.tween import get_swagger_versions
from pyramid_swagger.tween import handle_request
from pyramid_swagger.tween import noop_context
from pyramid_swagger.tween import prepare_body
from pyramid_swagger.tween import Settings
from pyramid_swagger.tween import should_exclude_path
from pyramid_swagger.tween import should_exclude_route
from pyramid_swagger.tween import SWAGGER_12, SWAGGER_20
from pyramid_swagger.tween import validate_response


def assert_eq_regex_lists(left, right):
    assert [r.pattern for r in left] == [r.pattern for r in right]


def test_default_exclude_paths():
    assert_eq_regex_lists(
        get_exclude_paths(Mock(settings={})),
        [re.compile(r) for r in DEFAULT_EXCLUDED_PATHS]
    )


def test_exclude_path_with_string():
    path_string = r'/foo/'
    registry = Mock(settings={'pyramid_swagger.exclude_paths': path_string})
    assert_eq_regex_lists(
        get_exclude_paths(registry),
        [re.compile(r) for r in [path_string]]
    )


def test_exclude_path_with_overrides():
    paths = [r'/foo/', r'/bar/']
    compiled = get_exclude_paths(
        Mock(settings={'pyramid_swagger.exclude_paths': paths}))
    assert_eq_regex_lists(
        compiled,
        [re.compile(r) for r in paths]
    )


def test_exclude_path_with_old_setting():
    # TODO(#63): remove deprecated `skip_validation` setting in v2.0.
    paths = [r'/foo/', r'/bar/']
    assert_eq_regex_lists(
        get_exclude_paths(
            Mock(settings={'pyramid_swagger.skip_validation': paths})),
        [re.compile(r) for r in paths]
    )


def test_response_charset_missing_raises_5xx():
    with pytest.raises(ResponseValidationError):
        prepare_body(
            Response(content_type='foo')
        )


@pytest.fixture
def mock_route_info():
    class MockRoute(object):
        name = 'route-one'

    return {'route': MockRoute}


def test_should_exclude_route(mock_route_info):
    assert should_exclude_route(set(['route-one', 'two']), mock_route_info)


def test_should_exclude_route_no_matched_route(mock_route_info):
    assert not should_exclude_route(set(['foo', 'two']), mock_route_info)


def test_should_exclude_route_no_route():
    assert not should_exclude_route(set(['foo', 'two']), {'route': None})


def test_validation_skips_path_properly():
    excluded_paths = [re.compile(r) for r in DEFAULT_EXCLUDED_PATHS]
    assert should_exclude_path(excluded_paths, '/static')
    assert should_exclude_path(excluded_paths, '/static/foobar')
    assert should_exclude_path(excluded_paths, '/api-docs')
    assert should_exclude_path(excluded_paths, '/api-docs/foobar')

    assert not should_exclude_path(excluded_paths, '/sample')
    assert not should_exclude_path(excluded_paths, '/sample/resources')


# TODO: Should probably be migrated to acceptance tests after we make mocking
# schemas easier there.
def test_validation_content_type_with_json():
    fake_schema = mock.Mock(response_body_schema={'type': 'object'})
    fake_validator = mock.Mock(schema=fake_schema)
    body = {'status': 'good'}
    response = Response(
        body=simplejson.dumps(body),
        headers={'Content-Type': 'application/json; charset=UTF-8'},
    )
    validator_map = mock.Mock(spec=ValidatorMap, response=fake_validator)
    validate_response(response, validator_map)
    fake_validator.validate.assert_called_once_with(body)


def test_skips_validating_errors():
    fake_schema = mock.Mock(response_body_schema={'type': 'string'})
    fake_validator = mock.Mock(schema=fake_schema)
    fake_validator_map = mock.Mock(response=fake_validator)
    response = Response(
        body='abe1351f',
        status_code=403,
    )
    validate_response(response, fake_validator_map)
    assert not fake_validator.validate.called


def test_raw_string():
    fake_schema = mock.Mock(response_body_schema={'type': 'string'})
    fake_validator = mock.Mock(spec=SchemaValidator, schema=fake_schema)
    response = Response(
        body='abe1351f',
        headers={'Content-Type': 'application/text; charset=UTF-8'},
    )
    validator_map = mock.Mock(spec=ValidatorMap, response=fake_validator)
    validate_response(response, validator_map)
    fake_validator.validate.assert_called_once_with(
        response.body.decode('utf-8'))


def build_mock_validator(properties):
    return mock.Mock(
        spec=['schema', 'validate'],
        schema={
            'properties': dict(
                (name, {'type': type_})
                for name, type_ in properties.items()
            )
        },
    )


def test_handle_request_returns_request_data():
    mock_request = mock.Mock(
        spec=PyramidSwaggerRequest,
        query={'int': '123', 'float': '3.14'},
        form={'form_int': '333', 'string2': 'xyz'},
        path={'path_int': '222', 'string': 'abc'},
        headers={'X-Is-Bool': 'True'},
        body={'more': 'foo'},
    )

    body_validator = build_mock_validator({'more': 'object'})
    body_validator.schema['name'] = 'bar'

    validator_map = mock.Mock(
        query=build_mock_validator({'int': 'integer', 'float': 'float'}),
        path=build_mock_validator({'path_int': 'integer', 'string': 'string'}),
        form=build_mock_validator({'form_int': 'integer'}),
        headers=build_mock_validator({'X-Is-Bool': 'boolean'}),
        body=body_validator,
    )

    expected = {
        'int': 123,
        'float': 3.14,
        'path_int': 222,
        'form_int': 333,
        'string': 'abc',
        'string2': 'xyz',
        'X-Is-Bool': True,
        'bar': {'more': 'foo'},
    }

    request_data = handle_request(mock_request, validator_map, noop_context,)
    assert request_data == expected


def test_get_op_for_request_found():
    request = Mock(spec=Request)
    route_info = {'route': Mock(spec=Route, path='/foo/{id}')}
    expected_op = Mock(spec=Operation)
    swagger_spec = Mock(spec=Spec,
                        get_op_for_request=Mock(return_value=expected_op))
    assert expected_op == get_op_for_request(request, route_info, swagger_spec)


def test_get_op_for_request_not_found_when_route_has_no_path():
    request = Mock(spec=Request, method='GET', url='http://localhost/foo/1')
    route_info = {'route': Mock(spec=[])}
    swagger_spec = Mock(spec=Spec)
    with pytest.raises(PathNotMatchedError) as excinfo:
        get_op_for_request(request, route_info, swagger_spec)
    assert 'Could not find a matching Swagger operation' in str(excinfo.value)


def test_get_op_for_request_not_found_when_no_match_in_swagger_spec():
    request = Mock(spec=Request, method='GET', url='http://localhost/foo/1')
    route_info = {'route': Mock(spec=Route, path='/foo/{id}')}
    mock_bravado_core_get_op_for_request = Mock(return_value=None)
    swagger_spec = Mock(
        spec=Spec, get_op_for_request=mock_bravado_core_get_op_for_request)
    with pytest.raises(PathNotMatchedError) as excinfo:
        get_op_for_request(request, route_info, swagger_spec)
    assert 'Could not find a matching Swagger operation' in str(excinfo.value)
    assert mock_bravado_core_get_op_for_request.call_count == 1


def test_get_swagger_versions_success():
    for versions in (['1.2'], ['2.0'], ['1.2', '2.0']):
        settings = {'pyramid_swagger.swagger_versions': versions}
        assert versions == get_swagger_versions(settings)


def test_get_swagger_versions_empty():
    settings = {'pyramid_swagger.swagger_versions': []}
    with pytest.raises(ValueError) as excinfo:
        get_swagger_versions(settings)
    assert 'pyramid_swagger.swagger_versions is empty' in str(excinfo.value)


def test_get_swagger_versions_unsupported():
    settings = {'pyramid_swagger.swagger_versions': ['10.0', '2.0']}
    with pytest.raises(ValueError) as excinfo:
        get_swagger_versions(settings)
    assert 'Swagger version 10.0 is not supported' in str(excinfo.value)


def test_validaton_error_decorator_transforms_SwaggerMappingError():

    @validation_error(RequestValidationError)
    def foo():
        raise SwaggerMappingError('kaboom')

    with pytest.raises(RequestValidationError) as excinfo:
        foo()
    assert 'kaboom' in str(excinfo.value)


@pytest.fixture
def registry():
    config = {
        'pyramid_swagger.schema12': None,
        'pyramid_swagger.schema20': None,
        }
    return Mock(settings=config)


@pytest.fixture
def settings():
    return Mock(spec=Settings)


def test_get_swagger20_objects_if_only_swagger20_version_is_present(
        settings, registry):
    registry.settings['pyramid_swagger.swagger_versions'] = [SWAGGER_20]
    registry.settings['pyramid_swagger.schema20'] = 'schema20'
    swagger_handler, spec = get_swagger_objects(settings, {}, registry)
    assert 'swagger20_handler' in str(swagger_handler)
    assert 'schema20' == spec


def test_get_swagger12_objects_if_only_swagger12_version_is_present(
        settings, registry):
    registry.settings['pyramid_swagger.swagger_versions'] = [SWAGGER_12]
    registry.settings['pyramid_swagger.schema12'] = 'schema12'
    swagger_handler, spec = get_swagger_objects(settings, {}, registry)
    assert 'swagger12_handler' in str(swagger_handler)
    assert 'schema12' == spec


def test_get_swagger20_objects_if_both_present_but_no_prefer20_config(
        settings, registry):
    registry.settings['pyramid_swagger.swagger_versions'] = [
        SWAGGER_12, SWAGGER_20]
    registry.settings['pyramid_swagger.schema20'] = 'schema20'
    swagger_handler, spec = get_swagger_objects(settings, {}, registry)
    assert 'swagger20_handler' in str(swagger_handler)
    assert 'schema20' == spec


def test_get_swagger20_objects_if_both_present_but_route_in_prefer20(
        settings, registry):
    settings.prefer_20_routes = ['swagger20_route']
    registry.settings['pyramid_swagger.swagger_versions'] = [
        SWAGGER_12, SWAGGER_20]
    route_info = {'route': Mock()}
    route_info['route'].name = 'swagger20_route'
    registry.settings['pyramid_swagger.schema20'] = 'schema20'
    swagger_handler, spec = get_swagger_objects(settings, route_info, registry)
    assert 'swagger20_handler' in str(swagger_handler)
    assert 'schema20' == spec


def test_get_swagger20_objects_if_both_present_but_request_has_no_route(
        settings, registry):
    settings.prefer_20_routes = ['swagger20_route']
    registry.settings['pyramid_swagger.swagger_versions'] = [
        SWAGGER_12, SWAGGER_20]
    registry.settings['pyramid_swagger.schema20'] = 'schema20'
    swagger_handler, spec = get_swagger_objects(settings, {}, registry)
    assert 'swagger20_handler' in str(swagger_handler)
    assert 'schema20' == spec


def test_get_swagger12_objects_if_both_present_but_route_not_in_prefer20(
        settings, registry):
    settings.prefer_20_routes = ['swagger20_route']
    registry.settings['pyramid_swagger.swagger_versions'] = [
        SWAGGER_12, SWAGGER_20]
    route_info = {'route': Mock()}
    route_info['route'].name = 'swagger12_route'
    registry.settings['pyramid_swagger.schema12'] = 'schema12'
    swagger_handler, spec = get_swagger_objects(settings, route_info, registry)
    assert 'swagger12_handler' in str(swagger_handler)
    assert 'schema12' == spec
