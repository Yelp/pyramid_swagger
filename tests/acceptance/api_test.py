# -*- coding: utf-8 -*-
import pytest

from pyramid.config import Configurator
from webtest import TestApp


@pytest.fixture(params=[True, False])
def use_default_view_configs(request):
    return request.param


@pytest.fixture
def custom_predicate():
    class Predicate(object):
        called = False

        def __init__(self, val, config):
            pass

        def text(self):
            return 'some text'

        phash = text

        def __call__(self, context, request):
            # Set on the class so we can check in the test
            type(self).called = True
            return True

    return Predicate


@pytest.fixture
def settings(use_default_view_configs):
    return {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
        'pyramid_swagger.use_default_view_configuration':
            use_default_view_configs,
    }


@pytest.fixture
def test_app(settings, custom_predicate, use_default_view_configs):
    """Fixture for setting up a test test_app."""
    config = Configurator(settings=settings)
    config.include('pyramid_swagger')
    config.add_view_predicate('predicate', custom_predicate)

    if not use_default_view_configs:
        config.add_pyramid_swagger_resource_listing_view(
            predicate=True,  # turn on custom predicate',
        )
        config.add_pyramid_swagger_api_declaration_views(
            predicate=True,  # turn on custom predicate
        )

    return TestApp(config.make_wsgi_app())


def test_api_docs(test_app, use_default_view_configs, custom_predicate):
    test_app.get(
        '/api-docs',
        status=200,
    )
    assert custom_predicate.called is not use_default_view_configs


def test_sample_resource(test_app, use_default_view_configs, custom_predicate):
    test_app.get(
        '/api-docs/sample',
        status=200,
    )
    assert custom_predicate.called is not use_default_view_configs


def test_other_sample_resource(
    test_app,
    use_default_view_configs,
    custom_predicate,
):
    test_app.get(
        '/api-docs/other_sample',
        status=200,
    )
    assert custom_predicate.called is not use_default_view_configs
