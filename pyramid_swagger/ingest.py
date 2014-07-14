from __future__ import unicode_literals

import os.path
import simplejson

from .load_schema import load_schema
from .model import SwaggerSchema
from .spec import validate_swagger_schemas


API_DOCS_FILENAME = 'api_docs.json'


class ResourceListingNotFoundError(Exception):
    pass


class ApiDeclarationNotFoundError(Exception):
    pass


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

    listing, listing_json = _load_resource_listing(schema_dir)

    return (
        listing,
        dict(
            (resource, resource_name_to_filepath(resource))
            for resource in find_resource_names(listing_json)
        )
    )


def _load_resource_listing(schema_dir):
    """Load the resource listing from file, handling errors.

    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :returns: (resource listing filepath, resource listing json)
    """
    resource_listing = os.path.join(schema_dir, API_DOCS_FILENAME)
    try:
        with open(resource_listing) as resource_listing_file:
            resource_listing_json = simplejson.load(resource_listing_file)
    # If not found, raise a more user-friendly error.
    except IOError:
        raise ResourceListingNotFoundError(
            'No resource listing found at {0}. Note that your json file '
            'must be named {1}'.format(resource_listing, API_DOCS_FILENAME)
        )
    return resource_listing, resource_listing_json


def compile_swagger_schema(schema_dir, should_validate_schemas):
    """Build a SwaggerSchema from various files.

    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :param should_validate_schemas: if True, check schemas for correctness
    :type should_validate_schemas: boolean
    :returns: a SwaggerSchema object
    """
    listing, mapping = build_schema_mapping(schema_dir)
    schema_resolvers = ingest_resources(
        listing,
        mapping,
        schema_dir,
        should_validate_schemas,
    )
    return SwaggerSchema(
        listing,
        mapping,
        schema_resolvers,
    )


def ingest_resources(listing, mapping, schema_dir, should_validate_schemas):
    """Consume the Swagger schemas and produce a queryable datastructure.

    :param listing: Filepath to a resource listing
    :type listing: string
    :param mapping: Map from resource name to filepath of its api declaration
    :type mapping: dict
    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :param should_validate_schemas: if True, check schemas for correctness
    :type should_validate_schemas: boolean
    :returns: A list of SchemaAndResolver objects
    """
    resource_filepaths = mapping.values()

    ingested_resources = []
    for name, filepath in mapping.items():
        try:
            ingested_resources.append(load_schema(filepath))
        # If we have trouble reading any files, raise a more user-friendly
        # error.
        except IOError:
            raise ApiDeclarationNotFoundError(
                'No api declaration found at {0}. Attempted to load the `{1}` '
                'resource relative to the schema_directory `{2}`. Perhaps '
                'your resource name and API declaration file do not '
                'match?'.format(filepath, name, schema_dir)
            )

    if should_validate_schemas:
        validate_swagger_schemas(
            listing,
            resource_filepaths
        )

    return ingested_resources
