# -*- coding: utf-8 -*-
import pytest
from webtest import TestApp

from .app import main


@pytest.fixture
def settings():
    dir_path = 'tests/sample_schemas/include_config_app/'
    return {
        'pyramid_swagger.schema_directory': dir_path,
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_swagger_spec_validation': True,
        'pyramid_swagger.swagger_versions': ['1.2', '2.0'],
    }


@pytest.fixture
def test_app_with_no_include_conf(settings):
    """Fixture for setting up a Swagger 2.0 version of the test test_app."""
    return TestApp(main({}, **settings))


@pytest.fixture
def test_app_with_include_conf(settings):
    """Fixture for setting up a Swagger 2.0 version of the test test_app."""
    settings['pyramid_swagger.include_2dot0_routes'] = ['standard']
    return TestApp(main({}, **settings))


def test_failure_with_no_include_config_case(test_app_with_no_include_conf):
    """The second get call should fail as it is not covered in v2.0 spec
    """
    response = test_app_with_no_include_conf.get('/sample/path_arg1/resource',
                                                 params={'required_arg': 'a'},)
    assert response.status_code == 200
    with pytest.raises(Exception):
        test_app_with_no_include_conf.get(
            '/sample/nonstring/1/1.1/true', params={},)


def test_success_with_include_config_case(test_app_with_include_conf):
    response = test_app_with_include_conf.get('/sample/path_arg1/resource',
                                              params={'required_arg': 'a'},)
    assert response.status_code == 200
    response = test_app_with_include_conf.get(
        '/sample/nonstring/1/1.1/true', params={},)
    assert response.status_code == 200
