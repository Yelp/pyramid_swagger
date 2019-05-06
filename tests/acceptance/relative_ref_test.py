# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import os.path
import re
import sys

import pytest
import yaml
from six import BytesIO
from webtest import TestApp as App

from tests.acceptance.app import main


DESERIALIZERS = {
    'json': lambda r: json.loads(r.body.decode('utf-8')),
    'yaml': lambda r: yaml.load(BytesIO(r.body)),
}


@pytest.fixture
def settings():
    dir_path = 'tests/sample_schemas/relative_ref/'
    return {
        'pyramid_swagger.schema_directory': dir_path,
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_swagger_spec_validation': True,
        'pyramid_swagger.swagger_versions': ['2.0']
    }


@pytest.fixture
def test_app(settings):
    """Fixture for setting up a Swagger 2.0 version of the test test_app."""
    return App(main({}, **settings))


@pytest.fixture
def test_app_deref(settings):
    """Fixture for setting up a Swagger 2.0 version of the test test_app
    test app serves swagger schemas with refs dereferenced."""
    settings['pyramid_swagger.dereference_served_schema'] = True
    return App(main({}, **settings))


def test_running_query_for_relative_ref(test_app):
    response = test_app.get('/sample/path_arg1/resource', params={},)
    assert response.status_code == 200


def translate_ref_extension(ref, schema_format):
    if schema_format == 'json':
        return ref  # all refs are already yaml
    return ref.replace('.json', '.%s' % schema_format)


def recursively_rewrite_refs(schema_item, schema_format):
    """
    Fix a schema's refs so that they all read the same format. Ensures that
    consumers requesting a yaml resource don't have to know how to read json.
    """
    if isinstance(schema_item, dict):
        for key, value in schema_item.items():
            if key == '$ref':
                schema_item[key] = translate_ref_extension(
                    value, schema_format,
                )
            else:
                recursively_rewrite_refs(value, schema_format)
    elif isinstance(schema_item, list):
        for item in schema_item:
            recursively_rewrite_refs(item, schema_format)


@pytest.mark.parametrize('schema_format', ['json', 'yaml', ])
def test_swagger_schema_retrieval(schema_format, test_app):
    here = os.path.dirname(__file__)
    deserializer = DESERIALIZERS[schema_format]

    expected_files = [
        'parameters/common',
        'paths/common',
        'responses/common',
        'swagger',
    ]
    for expected_file in expected_files:
        response = test_app.get(
            '/{0}.{1}'.format(expected_file, schema_format)
        )
        assert response.status_code == 200

        gold_path_parts = [
            here,
            '..',
            'sample_schemas',
            'relative_ref',
            '{0}.json'.format(expected_file),
        ]
        with open(os.path.join(*gold_path_parts)) as f:
            expected_dict = json.load(f)

        recursively_rewrite_refs(expected_dict, schema_format)

        actual_dict = deserializer(response)

        assert actual_dict == expected_dict


@pytest.mark.parametrize('schema_format', ['json', 'yaml', ])
def test_swagger_schema_retrieval_is_not_dereferenced(schema_format, test_app):

    response = test_app.get('/swagger.{0}'.format(schema_format))

    here = os.path.dirname(__file__)
    swagger_path_parts = [
        here,
        '..',
        'sample_schemas',
        'relative_ref',
        'dereferenced_swagger.json'
    ]
    dereferenced_swagger_path = os.path.join(*swagger_path_parts)
    with open(dereferenced_swagger_path) as swagger_file:
        expected_dict = json.load(swagger_file)

    deserializer = DESERIALIZERS[schema_format]
    actual_dict = deserializer(response)

    assert '"$ref"' in json.dumps(actual_dict)
    assert actual_dict != expected_dict


@pytest.mark.parametrize('schema_format', ['json', 'yaml', ])
def test_dereferenced_swagger_schema_retrieval(schema_format, test_app_deref):

    response = test_app_deref.get('/swagger.{0}'.format(schema_format))

    here = os.path.dirname(__file__)
    swagger_path_parts = [
        here,
        '..',
        'sample_schemas',
        'relative_ref',
        'dereferenced_swagger.json'
    ]
    dereferenced_swagger_path = os.path.join(*swagger_path_parts)
    with open(dereferenced_swagger_path) as swagger_file:
        expected_dict = json.load(swagger_file)

    deserializer = DESERIALIZERS[schema_format]
    actual_dict = deserializer(response)

    # pattern for references outside the current file
    ref_pattern = re.compile(r'("\$ref": "[^#][^"]*")')
    assert ref_pattern.findall(json.dumps(actual_dict)) == []

    if sys.platform != 'win32':
        # This checks that the returned dictionary matches the expected one
        # as this check mainly validates the bravado-core performs valid flattening
        # of specs and bravado-core flattening could provide different results
        # (in terms of references names) according to the platform we decided
        # to not check it for windows
        assert actual_dict == expected_dict
