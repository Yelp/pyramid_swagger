"""
Methods to help validate a given JSON document against the Swagger Spec.
"""
from pkg_resources import resource_filename

import jsonschema
import simplejson
from jsonschema.validators import RefResolver


def validate_swagger_schemas(resource_listing, resources):
    """Validate the structure of Swagger schemas against the spec.

    :param resource_listing: A filepath to a Swagger resource listing
    :type resource_listing: string
    :param resources: A list of filespaths to Swagger API declarations
    :type resources: [string]
    :raises: jsonschema ValidationErrors on malformed schemas
    """
    with open(resource_listing) as listing_file:
        validate_resource_listing(simplejson.load(listing_file))

    for resource in resources:
        with open(resource) as resource_file:
            resource_json = simplejson.load(resource_file)
        validate_api_declaration(resource_json)


def validate_resource_listing(resource_listing_json):
    resource_spec_path = resource_filename(
        'pyramid_swagger',
        'swagger_spec_schemas/v1.2/resourceListing.json'
    )
    validate_jsonschema(resource_spec_path, resource_listing_json)


def validate_api_declaration(api_declaration_json):
    """Validate a swagger schema.

    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    """
    api_spec_path = resource_filename(
        'pyramid_swagger',
        'swagger_spec_schemas/v1.2/apiDeclaration.json'
    )
    validate_jsonschema(api_spec_path, api_declaration_json)


def validate_jsonschema(spec_path, json_object):
    with open(spec_path) as schema_file:
        schema = simplejson.loads(schema_file.read())
        resolver = RefResolver(
            "file://{0}".format(spec_path),
            schema
        )
        jsonschema.validate(json_object, schema, resolver=resolver)
