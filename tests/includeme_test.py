import mock
import pytest

from jsonschema.exceptions import ValidationError
from pyramid.config import Configurator
import pyramid_swagger


@mock.patch('pyramid_swagger.register_api_doc_endpoints')
@mock.patch('pyramid_swagger.get_swagger_schema')
def test_disable_api_doc_views(_, mock_register):
    settings = {
        'pyramid_swagger.enable_api_doc_views': False,
        'pyramid_swagger.enable_swagger_spec_validation': False,
        'pyramid_swagger.schema': None,
    }
    mock_config = mock.Mock(
        spec=Configurator, registry=mock.Mock(settings=settings))
    pyramid_swagger.includeme(mock_config)
    assert not mock_register.called


def test_bad_schema_validated_on_include():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/bad_app/',
    }
    mock_config = mock.Mock(
        spec=Configurator, registry=mock.Mock(settings=settings))
    with pytest.raises(ValidationError) as excinfo:
        pyramid_swagger.includeme(mock_config)
    assert "'nickname' is a required property" in str(excinfo.value)


@mock.patch('pyramid_swagger.register_api_doc_endpoints')
@mock.patch('pyramid_swagger.get_swagger_schema')
def test_2dot0_schema_validated_on_include(_, _mock):
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/2.0/',
    }
    mock_config = mock.Mock(
        spec=Configurator, registry=mock.Mock(settings=settings))
    pyramid_swagger.includeme(mock_config)


def test_bad_schema_not_validated_if_spec_validation_is_disabled():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/bad_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    mock_config = mock.Mock(
        spec=Configurator, registry=mock.Mock(settings=settings))
    pyramid_swagger.includeme(mock_config)
