# -*- coding: utf-8 -*-
import pytest
from webtest import TestApp

from .app import main


@pytest.fixture
def settings():
    dir_path = 'tests/sample_schemas/prefer_20_routes_app/'
    return {
        'pyramid_swagger.schema_directory': dir_path,
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_swagger_spec_validation': True,
        'pyramid_swagger.swagger_versions': ['1.2', '2.0'],
    }


@pytest.fixture
def test_app_with_no_prefer_conf(settings):
    """Fixture for setting up a Swagger 2.0 version with no
    `prefer_20_routes` option added to settings."""
    return TestApp(main({}, **settings))


@pytest.fixture
def test_app_with_prefer_conf(settings):
    """Fixture for setting up a Swagger 2.0 version with a particular route
    `standard` added to `prefer_20_routes` option."""
    settings['pyramid_swagger.prefer_20_routes'] = ['standard']
    return TestApp(main({}, **settings))


def test_failure_with_no_prefer_config_case(test_app_with_no_prefer_conf):
    """The second get call should fail as it is not covered in v2.0 spec
    """
    response = test_app_with_no_prefer_conf.get('/sample/path_arg1/resource',
                                                params={'required_arg': 'a'},)
    assert response.status_code == 200
    with pytest.raises(Exception):
        test_app_with_no_prefer_conf.get(
            '/sample/nonstring/1/1.1/true', params={},)


def test_success_with_prefer_config_case(test_app_with_prefer_conf):
    response = test_app_with_prefer_conf.get('/sample/path_arg1/resource',
                                             params={'required_arg': 'a'},)
    assert response.status_code == 200
    response = test_app_with_prefer_conf.get(
        '/sample/nonstring/1/1.1/true', params={},)
    assert response.status_code == 200
