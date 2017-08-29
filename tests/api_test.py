# -*- coding: utf-8 -*-
import os

import mock
import pytest
import yaml
from bravado_core.spec import Spec
from pyramid.registry import Registry
from pyramid.request import Request
from pyramid.testing import DummyRequest
from pyramid.urldispatch import Route
from six.moves.urllib_parse import urljoin

from pyramid_swagger.api import build_swagger_12_api_declaration_view
from pyramid_swagger.api import extract_operation_from_request
from pyramid_swagger.api import extract_parameter_spec_from_request
from pyramid_swagger.api import get_path_if_relative
from pyramid_swagger.api import register_api_doc_endpoints
from pyramid_swagger.api import resolve_refs
from pyramid_swagger.ingest import API_DOCS_FILENAME
from pyramid_swagger.ingest import ApiDeclarationNotFoundError
from pyramid_swagger.ingest import ResourceListingNotFoundError
from pyramid_swagger.model import PathNotMatchedError
from pyramid_swagger.model import SwaggerSchema
from tests.acceptance.response_test import get_registry
from tests.acceptance.response_test import get_swagger_schema


def test_basepath_rewriting():
    resource_json = {'basePath': 'bar'}
    view = build_swagger_12_api_declaration_view(resource_json)
    request = DummyRequest(application_url='foo')
    result = view(request)
    assert result['basePath'] == request.application_url
    assert result['basePath'] != resource_json['basePath']


def build_config(schema_dir):
    return mock.Mock(
        registry=get_registry({
            'swagger_schema': get_swagger_schema(schema_dir),
        })
    )


def test_proper_error_on_missing_resource_listing():
    with pytest.raises(ResourceListingNotFoundError) as exc:
        register_api_doc_endpoints(
            build_config(
                'tests/sample_schemas/missing_resource_listing/api_docs.json'),
        )
    assert(
        'tests/sample_schemas/missing_resource_listing/' in str(exc)
    )
    assert 'must be named {0}'.format(API_DOCS_FILENAME) in str(exc)


def test_proper_error_on_missing_api_declaration():
    with pytest.raises(ApiDeclarationNotFoundError) as exc:
        register_api_doc_endpoints(
            build_config('tests/sample_schemas/missing_api_declaration/'),
        )
    assert (
        'tests/sample_schemas/missing_api_declaration/missing.json'
        in str(exc)
    )


def test_ignore_absolute_paths():
    """
    we don't have the ability to automagically translate these external
    resources from yaml to json and vice versa, so ignore them altogether.
    """
    assert get_path_if_relative(
        'http://www.google.com/some/special/schema.json',
    ) is None

    assert get_path_if_relative(
        '//www.google.com/some/schema.yaml',
    ) is None

    assert get_path_if_relative(
        '/usr/lib/shared/schema.json',
    ) is None


def test_resolve_nested_refs():
    """
    Make sure we resolve nested refs gracefully and not get lost in
    the recursion. Also make sure we don't rely on dictionary order
    """
    os.environ["PYTHONHASHSEED"] = str(1)
    with open('tests/sample_schemas/nested_defns/swagger.yaml') as swagger_spec:
        spec_dict = yaml.load(swagger_spec)
    spec = Spec.from_dict(spec_dict, '')
    resolve_refs(spec, spec_dict, ['/'], 'swagger', {})


def traverse_spec(swagger_spec):
    for k, v in swagger_spec.items():
        if k == "":
            raise Exception('Empty key detected in the swagger spec.')
        elif isinstance(v, dict):
            return traverse_spec(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    return traverse_spec(item)
    return


def test_extenal_refs_no_empty_keys():
    """
    This test ensures that we never use empty strings as
    keys swagger specs.
    """
    with open('tests/sample_schemas/external_refs/swagger.json') as swagger_spec:
        spec_dict = yaml.load(swagger_spec)
    path = 'file:' + os.getcwd() + '/tests/sample_schemas/external_refs/swagger.json'
    spec = Spec.from_dict(spec_dict, path)
    flattened_spec = resolve_refs(spec, spec_dict, ['/'], 'swagger', {})
    traverse_spec(flattened_spec)


@pytest.yield_fixture
def yaml_app(test_dir):
    spec_path = os.path.join(
        test_dir, 'sample_schemas/yaml_app/swagger.yaml',
    )
    with open(spec_path) as spec:
        swagger_spec_dict = yaml.safe_load(spec)
    yield Spec.from_dict(spec_dict=swagger_spec_dict, origin_url=urljoin('file://', spec_path))


@pytest.fixture
def mock_swagger20_request_extract_X_from_request(yaml_app):
    request = mock.Mock(spec=Request)
    request.matched_route = Route(name='api.route', pattern='/sample/{path_arg}/resource')
    request.method = 'GET'
    registry = Registry()
    registry.settings = {
        'pyramid_swagger.swagger_versions': ['2.0'],
        'pyramid_swagger.schema12': None,
        'pyramid_swagger.schema20': yaml_app,
    }
    request.registry = registry
    return request


@pytest.fixture(scope='session')
def mock_swagger12_request_extract_X_from_request():
    request = mock.Mock()
    request.matched_route = Route(name='api.route', pattern='/route')
    request.method = 'GET'
    registry = Registry()
    registry.settings = {
        'pyramid_swagger.swagger_versions': ['1.2'],
        'pyramid_swagger.schema12': mock.Mock(spec=SwaggerSchema),
        'pyramid_swagger.schema20': None,
    }
    request.registry = registry
    return request


def test_extract_operation_from_request_fail_if_not_Swagger20_spec(mock_swagger12_request_extract_X_from_request):
    with pytest.raises(AssertionError) as excinfo:
        extract_operation_from_request(request=mock_swagger12_request_extract_X_from_request)
    assert 'Swagger operation extraction is possible for Swagger2.0 endpoints only' in str(excinfo.value)


def test_extract_operation_from_request_fail_if_operation_not_found(mock_swagger20_request_extract_X_from_request):
    mock_swagger20_request_extract_X_from_request.matched_route.path = '/not_existing_endpoint'
    mock_swagger20_request_extract_X_from_request.matched_route.pattern = '/not_existing_endpoint'
    with pytest.raises(PathNotMatchedError) as excinfo:
        extract_operation_from_request(request=mock_swagger20_request_extract_X_from_request)
    assert 'Could not find a matching Swagger operation for {} request {}'.format(
        mock_swagger20_request_extract_X_from_request.method,
        mock_swagger20_request_extract_X_from_request.url,
    ) in str(excinfo.value)


def test_extract_operation_from_request_success(mock_swagger20_request_extract_X_from_request, yaml_app):
    operation = extract_operation_from_request(request=mock_swagger20_request_extract_X_from_request)
    assert yaml_app.spec_dict['paths'][mock_swagger20_request_extract_X_from_request.matched_route.pattern]['get'] == operation.op_spec


def test_extract_parameter_spec_from_request_parameter_not_found(mock_swagger20_request_extract_X_from_request, yaml_app):
    parameter_name = 'parameter_not_present'
    with pytest.raises(KeyError) as excinfo:
        extract_parameter_spec_from_request(
            request=mock_swagger20_request_extract_X_from_request, parameter_name=parameter_name,
        )
    assert parameter_name in str(excinfo.value)


def test_extract_parameter_spec_from_request_success(mock_swagger20_request_extract_X_from_request, yaml_app):
    operation_spec = yaml_app.spec_dict['paths'][mock_swagger20_request_extract_X_from_request.matched_route.pattern]['get']
    parameter_name = 'path_arg'
    expected_param = [
        param
        for param in operation_spec['parameters']
        if param['name'] == parameter_name
    ][0]

    param = extract_parameter_spec_from_request(request=mock_swagger20_request_extract_X_from_request, parameter_name=parameter_name)

    assert param == expected_param
