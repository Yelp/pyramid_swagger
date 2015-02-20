# -*- coding: utf-8 -*-
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
    return [api['path'].lstrip('/') for api in api_docs_json['apis']]


def build_schema_mapping(schema_dir, listing_json):
    """Discovers schema file locations and relations.

    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :param listing_json: the contents of the listing document
    :type  listing_json: string
    :returns: a mapping from resource name to file path
    :rtype: dict
    """
    def resource_name_to_filepath(name):
        return os.path.join(schema_dir, '{0}.json'.format(name))

    return dict(
        (resource, resource_name_to_filepath(resource))
        for resource in find_resource_names(listing_json)
    )


def _load_resource_listing(resource_listing):
    """Load the resource listing from file, handling errors.

    :param resource_listing: path to the api-docs resource listing file
    :type  resource_listing: string
    :returns: contents of the resource listing file
    :rtype: dict
    """
    try:
        with open(resource_listing) as resource_listing_file:
            return simplejson.load(resource_listing_file)
    # If not found, raise a more user-friendly error.
    except IOError:
        raise ResourceListingNotFoundError(
            'No resource listing found at {0}. Note that your json file '
            'must be named {1}'.format(resource_listing, API_DOCS_FILENAME)
        )


def compile_swagger_schema(schema_dir):
    """Build a SwaggerSchema from various files.

    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :returns: a SwaggerSchema object
    """
    listing_filename = os.path.join(schema_dir, API_DOCS_FILENAME)
    listing_json = _load_resource_listing(listing_filename)
    mapping = build_schema_mapping(schema_dir, listing_json)
    schema_resolvers = ingest_resources(mapping, schema_dir)
    return SwaggerSchema(listing_filename, mapping, schema_resolvers)


# TODO: more test cases
def add_swagger_schema(registry):
    """Add the swagger_schema to the registry.settings
    """
    schema_dir = registry.settings.get(
        'pyramid_swagger.schema_directory',
        'api_docs/'
    )
    if registry.settings.get(
        'pyramid_swagger.enable_swagger_spec_validation',
        True
    ):
        listing_filename = os.path.join(schema_dir, API_DOCS_FILENAME)
        # TODO: this will be replaced by ssv shortly
        listing_json = _load_resource_listing(listing_filename)
        mapping = build_schema_mapping(schema_dir, listing_json)
        validate_swagger_schemas(listing_filename, mapping.values())

    # TODO: docs for this
    if registry.settings.get(
        'pyramid_swagger.enable_build_swagger_schema_model',
        True
    ):
        registry.settings['swagger_schema'] = (
            compile_swagger_schema(schema_dir)
        )


def ingest_resources(mapping, schema_dir):
    """Consume the Swagger schemas and produce a queryable datastructure.

    :param mapping: Map from resource name to filepath of its api declaration
    :type mapping: dict
    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :returns: A list of :class:`pyramid_swagger.load_schema.SchemaAndResolver`
        objects
    """
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
    return ingested_resources
