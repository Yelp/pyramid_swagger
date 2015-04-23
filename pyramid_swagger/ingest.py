# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import glob
import os.path
import simplejson

from .load_schema import load_schema
from .model import SwaggerSchema
from .spec import API_DOCS_FILENAME, validate_swagger_schema


class ResourceListingNotFoundError(Exception):
    pass


class ApiDeclarationNotFoundError(Exception):
    pass


class ResourceListingGenerationError(Exception):
    pass


def find_resource_names(api_docs_json):
    return [api['path'].lstrip('/') for api in api_docs_json['apis']]


def find_resource_paths(schema_dir):
    """The inverse of :func:`find_resource_names` used to generate
    a resource listing from a directory of swagger api docs.
    """
    def not_api_doc_file(filename):
        return not filename.endswith(API_DOCS_FILENAME)

    def filename_to_path(filename):
        filename, _ext = os.path.splitext(os.path.basename(filename))
        return '/' + filename

    filenames = glob.glob('{0}/*.json'.format(schema_dir))
    return map(filename_to_path, filter(not_api_doc_file, sorted(filenames)))


def build_schema_mapping(schema_dir, resource_listing):
    """Discovers schema file locations and relations.

    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :param resource_listing: A swagger resource listing
    :type  resource_listing: dict
    :returns: a mapping from resource name to file path
    :rtype: dict
    """
    def resource_name_to_filepath(name):
        return os.path.join(schema_dir, '{0}.json'.format(name))

    return dict(
        (resource, resource_name_to_filepath(resource))
        for resource in find_resource_names(resource_listing)
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


def generate_resource_listing(schema_dir, listing_base):
    if 'apis' in listing_base:
        raise ResourceListingGenerationError(
            "{0}/{1} has an `apis` listing. Generating a listing would "
            "override this listing.".format(schema_dir, API_DOCS_FILENAME))

    return dict(
        listing_base,
        apis=[{'path': path} for path in find_resource_paths(schema_dir)]
    )


def get_resource_listing(schema_dir, should_generate_resource_listing):
    """Return the resource listing document.

    :param schema_dir: the directory which contains swagger spec files
    :type  schema_dir: string
    :param should_generate_resource_listing: when True a resource listing will
        be generated from the list of *.json files in the schema_dir. Otherwise
        return the contents of the resource listing file
    :type should_enerate_resource_listing: boolean
    :returns: the contents of a resource listing document
    """
    listing_filename = os.path.join(schema_dir, API_DOCS_FILENAME)
    resource_listing = _load_resource_listing(listing_filename)

    if not should_generate_resource_listing:
        return resource_listing
    return generate_resource_listing(schema_dir, resource_listing)


def compile_swagger_schema(schema_dir, resource_listing):
    """Build a SwaggerSchema from various files.

    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :returns: a SwaggerSchema object
    """
    mapping = build_schema_mapping(schema_dir, resource_listing)
    resource_validators = ingest_resources(mapping, schema_dir)
    return SwaggerSchema(resource_listing, mapping, resource_validators)


def get_swagger_schema(settings):
    """Return a :class:`pyramid_swagger.model.SwaggerSchema` constructed from
    the swagger specs in `pyramid_swagger.schema_directory`. If
    `pyramid_swagger.enable_swagger_spec_validation` is enabled the schema
    will be validated before returning it.

    :param settings: a pyramid registry settings with configuration for
        building a swagger schema
    :type settings: dict
    :returns: a :class:`pyramid_swagger.model.SwaggerSchema`
    """
    schema_dir = settings.get('pyramid_swagger.schema_directory', 'api_docs/')
    resource_listing = get_resource_listing(
        schema_dir,
        settings.get('pyramid_swagger.generate_resource_listing', False)
    )

    if settings.get('pyramid_swagger.enable_swagger_spec_validation', True):
        validate_swagger_schema(schema_dir, resource_listing)

    return compile_swagger_schema(schema_dir, resource_listing)


def ingest_resources(mapping, schema_dir):
    """Consume the Swagger schemas and produce a queryable datastructure.

    :param mapping: Map from resource name to filepath of its api declaration
    :type mapping: dict
    :param schema_dir: the directory schema files live inside
    :type schema_dir: string
    :returns: A list of mapping from :class:`RequestMatcher` to
        :class:`ValidatorMap`
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
