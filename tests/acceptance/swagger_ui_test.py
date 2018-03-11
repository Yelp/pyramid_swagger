# -*- coding: utf-8 -*-
import pytest
from webtest import TestApp as App

from .app import main


@pytest.fixture
def settings():
    return {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }


def custom_script_function(request, swagger_json_route):
    return '<script> replaced bootstrap </script>'


def test_api_explorer(settings):
    app = App(main({}, **settings))
    response = app.get('/api-explorer', status=200)
    assert response.text


def test_api_explorer_statics(settings):
    app = App(main({}, **settings))
    response = app.get('/pyramid_swagger/static/index.html',
                       status=200)
    assert response.text


def test_api_explorer_statics_location(settings):
    settings['pyramid_swagger.swagger_ui_static'] = 'foo'
    settings['pyramid_swagger.exclude_paths'] = '^/foo/?'
    app = App(main({}, **settings))
    response = app.get('/foo/index.html', status=200)
    assert response.text


def test_api_explorer_disabled(settings):
    settings['pyramid_swagger.swagger_ui_disable'] = True
    app = App(main({}, **settings))
    response = app.get('/api-explorer', status=404)
    assert response.text


def test_api_ui_default_bootstrap(settings):
    app = App(main({}, **settings))
    response = app.get('/api-explorer', status=200)
    assert 'url: "http://localhost/swagger.json"' in response.text
