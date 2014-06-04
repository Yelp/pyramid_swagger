"""
Methods for interacting with the Swagger Spec directly.
"""
from pkg_resources import resource_filename
from jsonschema.validators import RefResolver
import simplejson
import jsonschema


def validate_swagger_spec(swagger_spec_json):
    """Validate a swagger spec.

    :param swagger_spec_json: The spec to validate, as JSON
    :type swagger_spec_json: string
    """
    swagger_spec = simplejson.loads(swagger_spec_json)
    api_spec_path = resource_filename(
        'pyramid_swagger',
        'swagger_spec_schemas/v1.2/apiDeclaration.json'
    )
    with open(api_spec_path) as f:
        schema = simplejson.loads(f.read())
        resolver = RefResolver(
            "file://{0}".format(api_spec_path),
            schema
        )
        jsonschema.validate(swagger_spec, schema, resolver=resolver)
