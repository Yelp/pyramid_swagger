import os.path
import simplejson
from .load_schema import load_schema
from .swagger_spec import validate_swagger_schemas


def find_resource_names(api_docs_json, schema_dir):
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
    resource_listing = os.path.join(schema_dir, 'api_docs.json')
    with open(resource_listing) as resource_listing_file:
        resource_listing_json = simplejson.load(resource_listing_file)

    resource_filenames = [
        os.path.join(schema_dir, '{0}.json'.format(x))
        for x in find_resource_names(resource_listing_json, schema_dir)
    ]

    if should_validate_schemas:
        validate_swagger_schemas(resource_listing_json, resource_filenames)

    return [
        load_schema(resource)
        for resource in resource_filenames
    ]
