import jsonschema.exceptions
import pytest

import sys
from pyramid_swagger.swagger_spec import validate_swagger_spec


@pytest.mark.skipif(sys.version_info >= (3, 2), reason='See Issue #20')
def test_spec_validation_on_sample_spec():
    with open('tests/acceptance/app/swagger.json') as f:
        sample_json = f.read()
    validate_swagger_spec(sample_json)


@pytest.mark.skipif(sys.version_info >= (3, 2), reason='See Issue #20')
def test_spec_validation_on_malformed_spec():
    with open('tests/sample_malformed_swagger_spec.json') as f:
        sample_json = f.read()
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validate_swagger_spec(sample_json)
