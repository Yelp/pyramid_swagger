from __future__ import unicode_literals

import jsonschema
import os.path
import simplejson
from jsonschema.validators import RefResolver
from pkg_resources import resource_filename

from .load_schema import load_schema


API_DOCS_FILENAME = 'api_docs.json'


def find_resource_names(api_docs_json):
    return [
        api['path'].lstrip('/')
        for api in api_docs_json['apis']
    ]


def ingest_schema_files(schema_dir, should_validate_schemas):
    """Consume the Swagger schemas and produce a queryable datastructure.

    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :param should_validate_schemas: If True, will validate schemas against the
        Swagger 1.2 spec.
    :type should_validate_schemas: bool
    """
    resource_listing = os.path.join(schema_dir, API_DOCS_FILENAME)
    with open(resource_listing) as resource_listing_file:
        resource_listing_json = simplejson.load(resource_listing_file)

    resource_filepaths = [
        os.path.join(schema_dir, '{0}.json'.format(x))
        for x in find_resource_names(resource_listing_json)
    ]

    if should_validate_schemas:
        validate_swagger_schemas(resource_listing_json, resource_filepaths)

    return [
        load_schema(resource)
        for resource in resource_filepaths
    ]


def validate_swagger_schemas(resource_listing_json, resources):
    validate_resource_listing(resource_listing_json)
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
