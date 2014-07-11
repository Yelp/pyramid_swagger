import pytest
from webtest import TestApp

from .app import main


@pytest.fixture
def test_app():
    """Fixture for setting up a test test_app."""
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    return TestApp(main({}, **settings))


def test_api_docs(test_app):
    test_app.get(
        '/api-docs',
        status=200,
    )


def test_sample_resource(test_app):
    test_app.get(
        '/api-docs/sample',
        status=200,
    )


def test_other_sample_resource(test_app):
    test_app.get(
        '/api-docs/other_sample',
        status=200,
    )
