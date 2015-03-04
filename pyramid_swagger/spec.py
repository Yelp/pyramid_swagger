# -*- coding: utf-8 -*-
"""
Methods to help validate a given JSON document against the Swagger Spec.
"""
import os

from jsonschema.exceptions import ValidationError
import swagger_spec_validator

from .exceptions import wrap_exception
from .ingest import API_DOCS_FILENAME, SWAGGER_2DOT0_FILENAME


def fetch_swagger_spec_filename(schema_dir):
    """Try to find 2.0 spec(swagger.json), if unsuccessful,
    find 1.2 api doc(api_docs.json). Throw up if both fail
    """
    swagger20_filepath = os.path.join(schema_dir, SWAGGER_2DOT0_FILENAME)
    swagger12_filepath = os.path.join(schema_dir, API_DOCS_FILENAME)
    if os.path.isfile(swagger20_filepath):
        return swagger20_filepath
    if os.path.isfile(swagger12_filepath):
        return swagger12_filepath
    raise swagger_spec_validator.SwaggerValidationError(
        'No swagger spec found in directory:{0}. Note that your json file '
        'must be named {1} or {2}'.format(
            schema_dir, SWAGGER_2DOT0_FILENAME, API_DOCS_FILENAME))


@wrap_exception(ValidationError)
def validate_swagger_schema(schema_dir):
    """Validate the structure of Swagger schemas against the spec.

    :param schema_dir: A path to Swagger spec directory
    :type schema_dir: string
    :raises: :py:class:`swagger_spec_validator.SwaggerValidationError`
    """
    resource_listing = fetch_swagger_spec_filename(schema_dir)
    swagger_spec_validator.validate_spec_url(
        "file://{0}".format(os.path.abspath(resource_listing)))
