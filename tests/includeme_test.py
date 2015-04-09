import jsonschema
import mock
from pyramid.config import Configurator
from pyramid.registry import Registry
import pytest

import pyramid_swagger


@mock.patch('pyramid_swagger.register_api_doc_endpoints')
@mock.patch('pyramid_swagger.get_swagger_schema')
@mock.patch('pyramid_swagger.get_swagger_spec')
def test_disable_api_doc_views(_1, _2, mock_register):
    settings = {
        'pyramid_swagger.enable_api_doc_views': False,
        'pyramid_swagger.enable_swagger_spec_validation': False,
        'pyramid_swagger.schema': None,
    }

    mock_config = mock.Mock(
        spec=Configurator,
        registry=mock.Mock(spec=Registry, settings=settings))

    pyramid_swagger.includeme(mock_config)
    assert not mock_register.called


def test_bad_schema_validated_on_include():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/bad_app/',
    }
    mock_config = mock.Mock(registry=mock.Mock(settings=settings))
    with pytest.raises(jsonschema.exceptions.ValidationError):
        pyramid_swagger.includeme(mock_config)


@mock.patch('pyramid_swagger.get_swagger_spec')
def test_bad_schema_not_validated_if_spec_validation_is_disabled(_):
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/bad_app/',
        'pyramid_swagger.enable_swagger_spec_validation': False,
    }
    mock_config = mock.Mock(registry=mock.Mock(settings=settings))
    pyramid_swagger.includeme(mock_config)
