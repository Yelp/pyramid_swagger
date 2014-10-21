import pytest
import jsonschema.exceptions
import mock
from pyramid.config import Configurator
from pyramid.registry import Registry
from pyramid_swagger.tween import validation_tween_factory


def get_registry(settings):
    registry = Registry('testing')
    config = Configurator(registry=registry)
    if getattr(registry, 'settings', None) is None:
        config._set_settings(settings)
    config.commit()
    return registry


def test_bad_schema_validated_on_tween_creation_by_default():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/bad_app/',
    }
    registry = get_registry(settings=settings)
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validation_tween_factory(mock.ANY, registry)


def test_bad_schema_not_validated_if_spec_validation_is_disabled():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/bad_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    registry = get_registry(settings=settings)
    validation_tween_factory(mock.ANY, registry)
