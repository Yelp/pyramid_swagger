# -*- coding: utf-8 -*-
import base64

import pytest
from webtest import TestApp

from .app import main
from pyramid_swagger.tween import SwaggerFormat


@pytest.fixture
def settings():
    dir_path = 'tests/sample_schemas/'
    return {
        'pyramid_swagger.schema_file': 'swagger.txt',
        'pyramid_swagger.schema_directory': dir_path,
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_swagger_spec_validation': True,
    }


@pytest.fixture
def yaml_app():
    return SwaggerFormat(format='base64',
                         to_wire=base64.b64encode,
                         to_python=base64.b64decode,
                         validate=base64.b64decode,
                         description='base64')


def test_invalid_file_extension(settings, yaml_app):
    """Fixture for setting up a Swagger 2.0 version of the test testapp."""
    settings['pyramid_swagger.swagger_versions'] = ['2.0']
    settings['pyramid_swagger.user_formats'] = [yaml_app]

    with pytest.raises(Exception):
        TestApp(main({}, **settings))
