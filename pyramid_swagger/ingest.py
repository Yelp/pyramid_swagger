# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import glob
import os.path

import simplejson
from bravado_core.spec import build_http_handlers
from bravado_core.spec import Spec
from six.moves.urllib import parse as urlparse

from .api import build_swagger_12_endpoints
from .load_schema import load_schema
from .model import SwaggerSchema
from .spec import API_DOCS_FILENAME
from .spec import validate_swagger_schema


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

    def not_swagger_dot_json(filename):
        # Exclude a Swagger 2.0 schema file if it happens to exist.
        return not os.path.basename(filename) == 'swagger.json'

    def filename_to_path(filename):
        filename, _ext = os.path.splitext(os.path.basename(filename))
        return '/' + filename

    filenames = glob.glob('{0}/*.json'.format(schema_dir))
    return map(filename_to_path,
               filter(not_swagger_dot_json,
                      filter(not_api_doc_file, sorted(filenames))))


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
    endpoints = list(build_swagger_12_endpoints(resource_listing, mapping))
    return SwaggerSchema(endpoints, resource_validators)


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


def get_swagger_spec(settings):
    """Return a :class:`bravado_core.spec.Spec` constructed from
    the swagger specs in `pyramid_swagger.schema_directory`. If
    `pyramid_swagger.enable_swagger_spec_validation` is enabled the schema
    will be validated before returning it.

    :param settings: a pyramid registry settings with configuration for
        building a swagger schema
    :type settings: dict
    :rtype: :class:`bravado_core.spec.Spec`
    """
    schema_dir = settings.get('pyramid_swagger.schema_directory', 'api_docs/')
    schema_filename = settings.get('pyramid_swagger.schema_file',
                                   'swagger.json')
    schema_path = os.path.join(schema_dir, schema_filename)
    schema_url = urlparse.urljoin('file:', os.path.abspath(schema_path))

    handlers = build_http_handlers(None)  # don't need http_client for file:
    file_handler = handlers['file']
    spec_dict = file_handler(schema_url)

    return Spec.from_dict(
        spec_dict,
        config=create_bravado_core_config(settings),
        origin_url=schema_url)


def create_bravado_core_config(settings):
    """Create a configuration dict for bravado_core based on pyramid_swagger
    settings.

    :param settings: pyramid registry settings with configuration for
        building a swagger schema
    :type settings: dict
    :returns: config dict suitable for passing into
        bravado_core.spec.Spec.from_dict(..)
    :rtype: dict
    """
    # Map pyramid_swagger config key -> bravado_core config key
    config_keys = {
        'pyramid_swagger.enable_request_validation': 'validate_requests',
        'pyramid_swagger.enable_response_validation': 'validate_responses',
        'pyramid_swagger.enable_swagger_spec_validation':
            'validate_swagger_spec',
        'pyramid_swagger.use_models': 'use_models',
        'pyramid_swagger.user_formats': 'formats',
    }

    bravado_core_config_defaults = {
        'use_models': False
    }

    return dict(bravado_core_config_defaults, **dict(
        (bravado_core_key, settings[pyramid_swagger_key])
        for pyramid_swagger_key, bravado_core_key in config_keys.items()
        if pyramid_swagger_key in settings))


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
