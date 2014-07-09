from __future__ import unicode_literals

import os.path
import simplejson

from .load_schema import load_schema
from .spec import validate_swagger_schemas


API_DOCS_FILENAME = 'api_docs.json'


def find_resource_names(api_docs_json):
    return [
        api['path'].lstrip('/')
        for api in api_docs_json['apis']
    ]


def build_schema_mapping(schema_dir):
    """Discovers schema file locations and relations.

    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :returns: A tuple of (resource listing filepath, mapping) where the mapping
        is between resource name and file path
    :rtype: (string, dict)
    """
    def resource_name_to_filepath(name):
        return os.path.join(schema_dir, '{0}.json'.format(name))

    resource_listing = os.path.join(schema_dir, API_DOCS_FILENAME)
    with open(resource_listing) as resource_listing_file:
        resource_listing_json = simplejson.load(resource_listing_file)

    return (
        resource_listing,
        dict(
            (resource, resource_name_to_filepath(resource))
            for resource in find_resource_names(resource_listing_json)
        )
    )


def ingest_resources(listing, mapping, should_validate_schemas):
    """Consume the Swagger schemas and produce a queryable datastructure.

    :param listing: Filepath to a resource listing
    :type listing: string
    :param mapping: Map from resource name to filepath of its api declaration
    :type mapping: dict
    """
    resource_filepaths = mapping.values()
    if should_validate_schemas:
        validate_swagger_schemas(
            listing,
            resource_filepaths
        )

    return [
        load_schema(resource)
        for resource in resource_filepaths
    ]
