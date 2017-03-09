# -*- coding: utf-8 -*-
"""
Methods to help validate a given JSON document against the Swagger Spec.
"""
import os

import swagger_spec_validator
from jsonschema.exceptions import ValidationError

from .exceptions import wrap_exception

API_DOCS_FILENAME = 'api_docs.json'


@wrap_exception(ValidationError)
def validate_swagger_schema(schema_dir, resource_listing):
    """Validate the structure of Swagger schemas against the spec.

    **Valid only for Swagger v1.2 spec**

    Note: It is possible that resource_listing is not present in
    the schema_dir. The path is passed in the call so that ssv
    can fetch the api-declaration files from the path.

    :param resource_listing: Swagger Spec v1.2 resource listing
    :type resource_listing: dict
    :param schema_dir: A path to Swagger spec directory
    :type schema_dir: string
    :raises: :py:class:`swagger_spec_validator.SwaggerValidationError`
    """
    schema_filepath = os.path.join(schema_dir, API_DOCS_FILENAME)
    swagger_spec_validator.validator12.validate_spec(
        resource_listing,
        "file://{0}".format(os.path.abspath(schema_filepath)))
