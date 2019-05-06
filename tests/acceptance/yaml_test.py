# -*- coding: utf-8 -*-
from __future__ import absolute_import

import base64
import copy
import json

import pytest
import yaml
from bravado_core.schema import is_dict_like
from bravado_core.schema import is_list_like
from six import iterkeys
from webtest import TestApp as App

from pyramid_swagger.tween import SwaggerFormat
from tests.acceptance.app import main


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
    return App(main({}, **settings))


def test_user_format_happy_case(testapp_with_base64):
    response = testapp_with_base64.get('/sample/path_arg1/resource',
                                       params={'required_arg': 'MQ=='},)
    assert response.status_code == 200


def test_user_format_failure_case(testapp_with_base64):
    # 'MQ' is not a valid base64 encoded string.
    with pytest.raises(Exception):
        testapp_with_base64.get('/sample/path_arg1/resource',
                                params={'required_arg': 'MQ'},)


def _strip_xmodel(spec_dict):
    """
    :param spec_dict: Swagger spec in dict form. This is treated as read-only.
    :return: deep copy of spec_dict with the x-model vendor extension stripped out.
    """
    result = copy.deepcopy(spec_dict)

    def descend(fragment):
        if is_dict_like(fragment):
            fragment.pop('x-model', None)  # Removes 'x-model' key if present
            for key in iterkeys(fragment):
                descend(fragment[key])
        elif is_list_like(fragment):
            for element in fragment:
                descend(element)

    descend(result)
    return result


def validate_json_response(response, expected_dict):
    # webob < 1.7 returns the charset, webob >= 1.7 does not
    # see https://github.com/striglia/pyramid_swagger/issues/185
    assert response.headers['content-type'] in \
        ('application/json', 'application/json; charset=UTF-8')
    assert _strip_xmodel(json.loads(response.body.decode("utf-8"))) == expected_dict


def validate_yaml_response(response, expected_dict):
    assert response.headers['content-type'] == 'application/x-yaml; charset=UTF-8'
    assert _strip_xmodel(yaml.load(response.body)) == expected_dict


def _rewrite_ref(ref, schema_format):
    if schema_format == 'yaml':
        return ref  # all refs are already yaml
    return ref.replace('.yaml', '.%s' % schema_format)


def _recursively_rewrite_refs(schema_item, schema_format):
    if isinstance(schema_item, dict):
        for key, value in schema_item.items():
            if key == '$ref':
                schema_item[key] = _rewrite_ref(value, schema_format)
            else:
                _recursively_rewrite_refs(value, schema_format)
    elif isinstance(schema_item, list):
        for item in schema_item:
            _recursively_rewrite_refs(item, schema_format)


@pytest.mark.parametrize('schema_format', ['json', 'yaml'])
@pytest.mark.parametrize('test_file', ['swagger', 'defs'])
def test_swagger_json_api_doc_route(testapp_with_base64, test_file, schema_format):
    validation_method = {
        'yaml': validate_yaml_response,
        'json': validate_json_response,
    }

    url = '/%s.%s' % (test_file, schema_format)
    response = testapp_with_base64.get(url)
    assert response.status_code == 200

    fname = 'tests/sample_schemas/yaml_app/%s.yaml' % test_file
    with open(fname, 'r') as f:
        expected_schema = yaml.load(f)

    _recursively_rewrite_refs(expected_schema, schema_format)

    validation_method[schema_format](response, expected_schema)
