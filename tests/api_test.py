# -*- coding: utf-8 -*-
import os

import mock
import pytest
import yaml
from bravado_core.spec import Spec
from pyramid.testing import DummyRequest

from pyramid_swagger.api import build_swagger_12_api_declaration_view
from pyramid_swagger.api import get_path_if_relative
from pyramid_swagger.api import register_api_doc_endpoints
from pyramid_swagger.api import resolve_refs
from pyramid_swagger.ingest import API_DOCS_FILENAME
from pyramid_swagger.ingest import ApiDeclarationNotFoundError
from pyramid_swagger.ingest import ResourceListingNotFoundError
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
    with open('tests/sample_schemas/nested_defns/swagger.yaml') as swagger_spec:
        spec_dict = yaml.load(swagger_spec)
    spec = Spec.from_dict(spec_dict, '')
    for i in range(1, 50):
        os.environ["PYTHONHASHSEED"] = str(i)
        resolve_refs(spec, spec_dict, ['/'], 'swagger', {})
