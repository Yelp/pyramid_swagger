# -*- coding: utf-8 -*-
import pytest
from webtest import TestApp

from .app import main


@pytest.fixture
def settings():
    dir_path = 'tests/sample_schemas/relative_ref/'
    return {
        'pyramid_swagger.schema_directory': dir_path,
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_swagger_spec_validation': True,
    }


@pytest.fixture
def test_app(settings):
    """Fixture for setting up a Swagger 2.0 version of the test test_app."""
    settings['pyramid_swagger.swagger_versions'] = ['2.0']
    return TestApp(main({}, **settings))


def test_running_query_for_relative_ref(test_app):
    response = test_app.get('/sample/path_arg1/resource', params={},)
    assert response.status_code == 200
