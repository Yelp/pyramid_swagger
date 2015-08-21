from bravado_core.spec import Spec
import mock
from pyramid.config import Configurator
from pyramid.registry import Registry
import pytest
from swagger_spec_validator.common import SwaggerValidationError

import pyramid_swagger
from pyramid_swagger.model import SwaggerSchema


@mock.patch('pyramid_swagger.register_api_doc_endpoints')
@mock.patch('pyramid_swagger.get_swagger_schema')
@mock.patch('pyramid_swagger.get_swagger_spec')
def test_disable_api_doc_views(_1, _2, mock_register):
    settings = {
        'pyramid_swagger.enable_api_doc_views': False,
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }

    mock_config = mock.Mock(
        spec=Configurator,
        registry=mock.Mock(spec=Registry, settings=settings))

    pyramid_swagger.includeme(mock_config)
    assert not mock_register.called


def test_bad_schema_validated_on_include():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/bad_app/',
        'pyramid_swagger.enable_swagger_spec_validation': True,
    }
    mock_config = mock.Mock(registry=mock.Mock(settings=settings))
    with pytest.raises(SwaggerValidationError):
        pyramid_swagger.includeme(mock_config)
    # TODO: Figure out why this assertion fails on travis
    # assert "'info' is a required property" in str(excinfo.value)


@mock.patch('pyramid_swagger.get_swagger_spec')
def test_bad_schema_not_validated_if_spec_validation_is_disabled(_):
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/bad_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    mock_config = mock.Mock(
        spec=Configurator, registry=mock.Mock(settings=settings))
    pyramid_swagger.includeme(mock_config)


@mock.patch('pyramid_swagger.register_api_doc_endpoints')
def test_swagger_12_only(mock_register):
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.swagger_versions': ['1.2']
    }
    mock_config = mock.Mock(registry=mock.Mock(settings=settings))
    pyramid_swagger.includeme(mock_config)
    assert isinstance(settings['pyramid_swagger.schema12'], SwaggerSchema)
    assert mock_register.call_count == 1


@mock.patch('pyramid_swagger.register_api_doc_endpoints')
def test_swagger_20_only(mock_register):
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.swagger_versions': ['2.0']
    }
    mock_config = mock.Mock(registry=mock.Mock(settings=settings))
    pyramid_swagger.includeme(mock_config)
    assert isinstance(settings['pyramid_swagger.schema20'], Spec)
    assert not settings['pyramid_swagger.schema12']
    assert mock_register.call_count == 1


@mock.patch('pyramid_swagger.register_api_doc_endpoints')
def test_swagger_12_and_20(mock_register):
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.swagger_versions': ['1.2', '2.0']
    }
    mock_config = mock.Mock(registry=mock.Mock(settings=settings))
    pyramid_swagger.includeme(mock_config)
    assert isinstance(settings['pyramid_swagger.schema20'], Spec)
    assert isinstance(settings['pyramid_swagger.schema12'], SwaggerSchema)
    assert mock_register.call_count == 2
