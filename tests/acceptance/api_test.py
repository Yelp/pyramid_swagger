import pytest


@pytest.fixture
def test_app(settings=None):
    """Fixture for setting up a test test_app with particular settings."""
    from .app import main
    from webtest import TestApp
    settings = settings or dict({
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
    })
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
