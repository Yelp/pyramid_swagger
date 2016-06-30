# -*- coding: utf-8 -*-
import json
import os.path
import pytest
import yaml

from six import BytesIO
from webtest import TestApp
from .app import main


DESERIALIZERS = {
    'json': lambda r: json.loads(r.body.decode('utf-8')),
    'yaml': lambda r: yaml.load(BytesIO(r.body)),
}


@pytest.fixture
def settings():
    project_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..')
    )
    dir_path = '{project}/tests/sample_schemas/{directory}'.format(
        project=project_path,
        directory='recursive_app/external',
    )
    return {
        'pyramid_swagger.schema_directory': dir_path,
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_swagger_spec_validation': True,
        'pyramid_swagger.swagger_versions': ['2.0']
    }


@pytest.fixture
def test_app_deref(settings):
    """Fixture for setting up a Swagger 2.0 version of the test test_app
    test app serves swagger schemas with refs dereferenced."""
    settings['pyramid_swagger.dereference_served_schema'] = True
    return TestApp(main({}, **settings))


@pytest.mark.parametrize('schema_format', ['json', 'yaml', ])
def test_dereferenced_swagger_schema_bravado_client(
        schema_format,
        test_app_deref,
):
    from bravado.client import SwaggerClient

    response = test_app_deref.get('/swagger.{0}'.format(schema_format))
    deserializer = DESERIALIZERS[schema_format]
    specs = deserializer(response)

    SwaggerClient.from_spec(specs)
