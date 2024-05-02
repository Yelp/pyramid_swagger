# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os

import pytest
from webtest import TestApp as App

from tests.acceptance.app import main


@pytest.fixture
def settings():
    return {
        'pyramid_swagger.schema_directory': os.path.join('tests', 'sample_schemas', 'good_app'),
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }


@pytest.fixture
def default_test_app(settings):
    return App(main({}, **settings))


@pytest.fixture
def swagger_20_test_app(settings):
    """Fixture for setting up a Swagger 2.0 version of the test test_app."""
    settings['pyramid_swagger.swagger_versions'] = ['2.0']
    return App(main({}, **settings))


@pytest.fixture
def swagger_12_test_app(settings):
    """Fixture for setting up a Swagger 1.2 version of the test test_app."""
    settings['pyramid_swagger.swagger_versions'] = ['1.2']
    return App(main({}, **settings))


@pytest.fixture
def swagger_12_and_20_test_app(settings):
    """Fixture for setting up a Swagger 1.2 and Swagger 2.0 version of the
    test test_app.
    """
    settings['pyramid_swagger.swagger_versions'] = ['1.2', '2.0']
    return App(main({}, **settings))


@pytest.mark.skip(reason="Deprecated swagger 1.2 tests are broken. Skip instead of fixing.")
def test_12_api_docs(swagger_12_test_app):
    response = swagger_12_test_app.get('/api-docs', status=200)
    assert response.json['swaggerVersion'] == '1.2'


@pytest.mark.skip(reason="Deprecated swagger 1.2 tests are broken. Skip instead of fixing.")
def test_12_sample_resource(swagger_12_test_app):
    response = swagger_12_test_app.get('/api-docs/sample', status=200)
    assert response.json['swaggerVersion'] == '1.2'


@pytest.mark.skip(reason="Deprecated swagger 1.2 tests are broken. Skip instead of fixing.")
def test_12_other_sample_resource(swagger_12_test_app):
    response = swagger_12_test_app.get('/api-docs/other_sample', status=200)
    assert response.json['swaggerVersion'] == '1.2'


def test_20_schema(swagger_20_test_app):
    response = swagger_20_test_app.get('/swagger.json', status=200)
    assert response.json['swagger'] == '2.0'


@pytest.mark.skip(reason="Deprecated swagger 1.2 tests are broken. Skip instead of fixing.")
def test_12_and_20_schemas(swagger_12_and_20_test_app):
    for path in ('/api-docs', '/api-docs/sample', '/api-docs/other_sample'):
        response12 = swagger_12_and_20_test_app.get(path, status=200)
        assert response12.json['swaggerVersion'] == '1.2'

    response20 = swagger_12_and_20_test_app.get('/swagger.json', status=200)
    assert response20.json['swagger'] == '2.0'


def test_default_only_serves_up_swagger_20_schema(default_test_app):
    response = default_test_app.get('/swagger.json', status=200)
    assert response.json['swagger'] == '2.0'

    # swagger 1.2 schemas should 404
    for path in ('/api-docs', '/api-docs/sample', '/api-docs/other_sample'):
        default_test_app.get(path, status=404)


def test_recursive_swagger_api_internal_refs():
    recursive_test_app = App(main({}, **{
        'pyramid_swagger.schema_directory':
            'tests/sample_schemas/recursive_app/internal/',
    }))

    recursive_test_app.get('/swagger.json', status=200)


def test_recursive_swagger_api_external_refs():
    recursive_test_app = App(main({}, **{
        'pyramid_swagger.schema_directory':
            'tests/sample_schemas/recursive_app/external/',
    }))

    recursive_test_app.get('/swagger.json', status=200)
    recursive_test_app.get('/external.json', status=200)


def test_base_path_api_docs_on_good_app_schema():
    base_path = '/web/base/path'

    recursive_test_app = App(main({}, **{
        'pyramid_swagger.schema_directory':
            'tests/sample_schemas/good_app/',
        'pyramid_swagger.base_path_api_docs':
            base_path
    }))

    recursive_test_app.get(base_path + '/swagger.json', status=200)
    recursive_test_app.get('/swagger.json', status=404)


def test_base_path_api_docs_on_recursive_app_schema():
    base_path = '/some/path'
    recursive_test_app = App(main({}, **{
        'pyramid_swagger.schema_directory':
            'tests/sample_schemas/recursive_app/external/',
        'pyramid_swagger.base_path_api_docs':
            base_path
    }))

    recursive_test_app.get(base_path + '/swagger.json', status=200)
    recursive_test_app.get('/swagger.json', status=404)
    recursive_test_app.get(base_path + '/external.json', status=200)
    recursive_test_app.get('/external.json', status=404)


def test_base_path_api_docs_with_script_name_on_recursive_app_schema():
    base_path = '/some/path'
    script_name = '/scriptname'
    test_app = App(main({}, **{
        'pyramid_swagger.schema_directory':
            'tests/sample_schemas/recursive_app/external/',
        'pyramid_swagger.base_path_api_docs':
            base_path}),
        {'SCRIPT_NAME': script_name})

    test_app.get(script_name + base_path + '/swagger.json', status=200)
    test_app.get('/swagger.json', status=404)

    test_app.get(script_name + base_path + '/external.json', status=200)
    test_app.get('/external.json', status=404)


def test_virtual_subpath(settings):
    test_app = App(main({}, **settings), {'SCRIPT_NAME': '/subpath'})
    test_app.get('/subpath/swagger.json', status=200)
