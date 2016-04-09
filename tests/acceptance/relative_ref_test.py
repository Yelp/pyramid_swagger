# -*- coding: utf-8 -*-
import json
import os.path
import pytest
import yaml

from six import BytesIO
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


def fix_ref(ref, schema_format):
    if schema_format == 'json':
        return ref  # all refs are already yaml
    return ref.replace('.json', '.%s' % schema_format)


def walk_schema_for_refs(schema_item, schema_format):
    if isinstance(schema_item, dict):
        for key, value in schema_item.items():
            if key == '$ref':
                schema_item[key] = fix_ref(value, schema_format)
            else:
                walk_schema_for_refs(value, schema_format)
    elif isinstance(schema_item, list):
        for item in schema_item:
            walk_schema_for_refs(item, schema_format)


@pytest.mark.parametrize('schema_format', ['json', 'yaml'])
def test_swagger_schema_retrieval(schema_format, test_app):
    here = os.path.dirname(__file__)
    deserializers = {
        'json': lambda r: json.loads(r.body.decode('utf-8')),
        'yaml': lambda r: yaml.load(BytesIO(r.body)),
    }

    deserializer = deserializers[schema_format]

    expected_files = [
        'parameters/common',
        'paths/common',
        'responses/common',
        'swagger',
    ]
    for expected_file in expected_files:
        response = test_app.get('/%s.%s' % (expected_file, schema_format))
        assert response.status_code == 200

        gold_path_parts = [
            here, '..', 'sample_schemas', 'relative_ref',
            '%s.json' % expected_file,
        ]
        with open(os.path.join(*gold_path_parts)) as f:
            expected_dict = json.load(f)

        walk_schema_for_refs(expected_dict, schema_format)

        actual_dict = deserializer(response)

        assert actual_dict == expected_dict
