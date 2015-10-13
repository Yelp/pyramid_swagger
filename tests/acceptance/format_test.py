# -*- coding: utf-8 -*-
import base64

import pytest
from webtest import TestApp

from .app import main
from pyramid_swagger.tween import SwaggerFormat


@pytest.fixture
def settings():
    dir_path = 'tests/sample_schemas/user_format/'
    return {
        'pyramid_swagger.schema_directory': dir_path,
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_swagger_spec_validation': True,
    }


@pytest.fixture
def user_format():
    return SwaggerFormat(format='base64',
                         to_wire=base64.b64encode,
                         to_python=base64.b64decode,
                         validate=base64.b64decode,
                         description='base64')


@pytest.fixture
def testapp_with_base64(settings, user_format):
    """Fixture for setting up a Swagger 2.0 version of the test testapp."""
    settings['pyramid_swagger.swagger_versions'] = ['2.0']
    settings['pyramid_swagger.user_formats'] = [user_format]
    return TestApp(main({}, **settings))


def test_user_format_happy_case(testapp_with_base64):
    response = testapp_with_base64.get('/sample/path_arg1/resource',
                                       params={'required_arg': 'MQ=='},)
    assert response.status_code == 200


def test_user_format_failure_case(testapp_with_base64):
    # 'MQ' is not a valid base64 encoded string.
    with pytest.raises(Exception):
        testapp_with_base64.get('/sample/path_arg1/resource',
                                params={'required_arg': 'MQ'},)
