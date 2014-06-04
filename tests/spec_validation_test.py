import jsonschema.exceptions
import pytest

from pyramid_swagger.swagger_spec import validate_swagger_spec


def test_spec_validation_on_sample_spec():
    with open('tests/sample_swagger_spec.json') as f:
        sample_json = f.read()
    validate_swagger_spec(sample_json)


def test_spec_validation_on_malformed_spec():
    with open('tests/sample_malformed_swagger_spec.json') as f:
        sample_json = f.read()
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validate_swagger_spec(sample_json)
