# -*- coding: utf-8 -*-
import mock
import pytest

from jsonschema.exceptions import ValidationError
from swagger_spec_validator import SwaggerValidationError

from pyramid_swagger.spec import (API_DOCS_FILENAME,
                                  SWAGGER_2DOT0_FILENAME,
                                  fetch_swagger_spec_filename,
                                  validate_swagger_schema)


@mock.patch('os.path.isfile')
def test_fetch_swagger_filename_prefers_2dot0(mock_isfile):
    def return_true_for_swagger2(filepath):
        return filepath.endswith(SWAGGER_2DOT0_FILENAME)

    mock_isfile.side_effect = return_true_for_swagger2
    assert ('/foo/' + SWAGGER_2DOT0_FILENAME ==
            fetch_swagger_spec_filename('/foo'))


@mock.patch('os.path.isfile')
def test_fetch_swagger_filename_fallsback_to_1dot2(mock_isfile):
    def return_true_for_swagger12(filepath):
        return filepath.endswith(API_DOCS_FILENAME)

    mock_isfile.side_effect = return_true_for_swagger12
    assert ('/foo/' + API_DOCS_FILENAME ==
            fetch_swagger_spec_filename('/foo'))


@mock.patch('os.path.isfile')
def test_fetch_swagger_filename_raises_if_spec_not_found(mock_isfile):
    mock_isfile.return_value = False
    with pytest.raises(SwaggerValidationError):
        fetch_swagger_spec_filename('/foo')


def test_proper_error_on_missing_resource_listing():
    with pytest.raises(ValidationError) as exc:
        validate_swagger_schema(
            'tests/sample_schemas/missing_resource_listing/')
    assert(
        'tests/sample_schemas/missing_resource_listing/'
        in str(exc)
    )


def test_proper_error_on_missing_api_declaration():
    with pytest.raises(ValidationError) as exc:
        validate_swagger_schema(
            'tests/sample_schemas/missing_api_declaration/')
    assert (
        'tests/sample_schemas/missing_api_declaration/missing.json'
        in str(exc)
    )
