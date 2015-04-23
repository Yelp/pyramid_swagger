# -*- coding: utf-8 -*-
import os
import pytest

import simplejson
from jsonschema.exceptions import ValidationError

from pyramid_swagger.spec import API_DOCS_FILENAME, validate_swagger_schema


def test_success_for_good_app():
    dir_path = 'tests/sample_schemas/good_app/'
    with open(os.path.join(dir_path, API_DOCS_FILENAME)) as f:
        resource_listing = simplejson.load(f)
        validate_swagger_schema(dir_path, resource_listing)


def test_proper_error_on_missing_api_declaration():
    with pytest.raises(ValidationError) as exc:
        dir_path = 'tests/sample_schemas/missing_api_declaration/'
        with open(os.path.join(dir_path, API_DOCS_FILENAME)) as f:
            resource_listing = simplejson.load(f)
            validate_swagger_schema(dir_path, resource_listing)

    assert "{0}{1}".format(dir_path, "missing.json") in str(exc)
