# -*- coding: utf-8 -*-
import base64

import pytest
from webtest import TestApp

from .app import main
from pyramid_swagger.tween import SwaggerFormat


@pytest.fixture
def settings():
    dir_path = 'tests/sample_schemas/yaml_app/'
    return {
        'pyramid_swagger.schema_file': 'swagger.yaml',
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


@pytest.fixture
def testapp_with_base64(settings, yaml_app):
    """Fixture for setting up a Swagger 2.0 version of the test testapp."""
    settings['pyramid_swagger.swagger_versions'] = ['2.0']
    settings['pyramid_swagger.user_formats'] = [yaml_app]
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


def test_swagger_json_api_doc_route(testapp_with_base64):
    expected_schema = {
        'host': 'localhost:9999',
        'info': {
            'title': 'Title was not specified',
            'version': '0.1',
        },
        'produces': ['application/json'],
        'schemes': ['http'],
        'swagger': '2.0',
        'paths': {
            '/sample/{path_arg}/resource': {
                'get': {
                    'description': '',
                    'operationId': 'standard',
                    'parameters': [
                        {
                            'enum': ['path_arg1', 'path_arg2'],
                            'in': 'path',
                            'name': 'path_arg',
                            'required': True,
                            'type': 'string',
                        }, {
                            'format': 'base64',
                            'in': 'query',
                            'name': 'required_arg',
                            'required': True,
                            'type': 'string',
                        }, {
                            'in': 'query',
                            'name': 'optional_arg',
                            'required': False,
                            'type': 'string',
                        },
                    ],
                    'responses': {
                        '200': {
                            'description': 'Return a standard_response',
                            'schema': {
                                'additionalProperties': False,
                                'properties': {
                                    'logging_info': {'type': 'object'},
                                    'raw_response': {'type': 'string'},
                                },
                                'required': [
                                    'raw_response',
                                    'logging_info',
                                ],
                                'type': 'object',
                            },
                        },
                    },
                },
                'post': {
                    'parameters': [
                        {
                            'in': 'path',
                            'name': 'path_arg',
                            'required': True,
                            'type': 'string',
                        }, {
                            'in': 'body',
                            'name': 'request',
                            'required': True,
                            'schema': {
                                'additionalProperties': False,
                                'properties': {
                                    'bar': {'type': 'string'},
                                    'foo': {'type': 'string'},
                                },
                                'required': ['foo'],
                                'type': 'object',
                            },
                        },
                    ],
                    'responses': {
                        'default': {
                            'description': 'test '
                            'response',
                            'schema': {
                                'additionalProperties': False,
                                'properties': {
                                    'logging_info': {'type': 'object'},
                                    'raw_response': {'type': 'string'},
                                },
                                'required': [
                                    'raw_response',
                                    'logging_info'
                                ],
                                'type': 'object',
                            },
                        },
                    },
                },
            },
        },
    }

    response = testapp_with_base64.get(
        '/swagger.json',
    )
    assert response.status_code == 200
    assert response.headers['content-type'] == ('application/json; '
                                                'charset=UTF-8')
    import json
    assert json.loads(response.body.decode("utf-8")) == expected_schema

    response = testapp_with_base64.get(
        '/swagger.yaml',
    )
    assert response.status_code == 200
    assert response.headers['content-type'] == ('application/x-yaml; '
                                                'charset=UTF-8')
    import yaml
    assert yaml.load(response.body) == expected_schema
