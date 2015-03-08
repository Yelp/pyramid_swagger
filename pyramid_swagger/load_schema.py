# -*- coding: utf-8 -*-
"""
Module to load swagger specs and build efficient data structures for querying
them during request validation.
"""
from __future__ import unicode_literals
from collections import namedtuple

import simplejson
from jsonschema import RefResolver


def build_param_schema(schema, param_type):
    """Turn a swagger endpoint schema into an equivalent one to validate our
    request.

    As an example, this would take this swagger schema:
        {
            "paramType": "query",
            "name": "query",
            "description": "Location to query",
            "type": "string",
            "required": true
        }
    To this jsonschema:
        {
            "type": "object",
            "additionalProperties": "False",
            "properties:": {
                "description": "Location to query",
                "type": "string",
                "required": true
            }
        }
    Which we can then validate against a JSON object we construct from the
    pyramid request.
    """
    properties = dict(
        (s['name'], strip_swagger_markup(s))
        for s in schema['parameters']
        if s['paramType'] == param_type
    )
    # Generate a jsonschema that describes the set of all query parameters. We
    # can then validate this against dict(request.params).
    if properties:
        return {
            'type': 'object',
            'properties': properties,
            'additionalProperties': False,
        }
    else:
        return None


# TODO: do this with jsonschema directly
def extract_body_schema(schema, models_schema):
    """Turn a swagger endpoint schema into an equivalent one to validate our
    request.

    As an example, this would take this swagger schema:
        {
            "paramType": "body",
            "name": "body",
            "description": "json list: [ll1,ll2]",
            "type": "array",
            "items": {
                "$ref": "GeoPoint"
            },
            "required": true
        }
    To this jsonschema:
        {
            "type": "array",
            "items": {
                "$ref": "GeoPoint"
            },
        }
    Which we can then validate against a JSON object we construct from the
    pyramid request.
    """
    matching_body_schemas = [
        s
        for s in schema['parameters']
        if s['paramType'] == 'body'
    ]
    if matching_body_schemas:
        schema = matching_body_schemas[0]
        type_ref = extract_validatable_type(schema['type'], models_schema)
        # Unpleasant, but we are forced to replace 'type' defns with proper
        # jsonschema refs.
        if '$ref' in type_ref:
            del schema['type']
            schema.update(type_ref)
        return strip_swagger_markup(schema)
    else:
        return None


# TODO: do this with jsonschema directly
def strip_swagger_markup(schema):
    """Turn a swagger URL parameter schema into a raw jsonschema.

    Involves just removing various swagger-specific markup tags.
    """
    swagger_specific_keys = (
        'paramType',
        'name',
    )
    return dict(
        (k, v)
        for k, v in schema.items()
        if k not in swagger_specific_keys
    )


def get_model_resolver(schema):
    """
    Get a RefResolver. RefResolver's will resolve "$ref:
    ObjectType" entries in the schema, which are used to describe more complex
    objects.

    :returns: The RefResolver for the schema's models.
    :rtype: RefResolver
    """
    models = dict(
        (k, strip_swagger_markup(v))
        for k, v in schema.get('models', {}).items()
    )
    return RefResolver('', '', models)


class SchemaMap(namedtuple(
    'SchemaMap', [
        'request_query_schema',
        'request_path_schema',
        'request_header_schema',
        'request_body_schema',
        'response_body_schema'
    ])):
    """
    A SchemaMap contains a mapping from incoming paths to schemas for request
    queries, request bodies, and responses. This requires some precomputation
    but means we can do fast query-time validation without having to walk over
    the schema.
    """
    __slots__ = ()

    @classmethod
    def from_operation(cls, operation, models):
        return cls(
            build_param_schema(operation, 'query'),
            build_param_schema(operation, 'path'),
            build_param_schema(operation, 'header'),
            extract_body_schema(operation, models),
            extract_response_body_schema(operation, models),
        )


def build_request_to_schemas_map(schema):
    """Take the swagger schema and build a map from incoming path to a
    jsonschema for requests and responses."""
    schema_models = schema.get('models', {})
    for api in schema['apis']:
        path = api['path']
        for operation in api['operations']:
            # Now that we have the necessary info for this particular
            # path/method combination, build our dict.
            key = (path, operation['method'])
            yield key, SchemaMap.from_operation(operation, schema_models)


# TODO: do this with jsonschema directly
def extract_response_body_schema(operation, schema_models):
    if operation['type'] in schema_models:
        return extract_validatable_type(operation['type'], schema_models)
    else:
        acceptable_fields = (
            'type', '$ref', 'format', 'defaultValue', 'enum', 'minimum',
            'maximum', 'items', 'uniqueItems'
        )

        return dict([
            (field, operation[field])
            for field in acceptable_fields
            if field in operation
        ])


# TODO: do this with jsonschema directly
def extract_validatable_type(type_name, models):
    """Returns a jsonschema-compatible typename from the Swagger type.

    This is necessary because for our Swagger specs to be compatible with
    swagger-ui, they must not use a $ref to internal models.

    :returns: A key-value that jsonschema can validate. Key will be either
        'type' or '$ref' as is approriate.
    :rtype: dict
    """
    if type_name in models:
        return {'$ref': type_name}
    else:
        return {'type': type_name}


class SchemaAndResolver(namedtuple(
        'SAR',
        ['request_to_schema_map', 'resolver'])):
    __slots__ = ()


def load_schema(schema_path):
    """Prepare the schema so we can make fast validation comparisons.

    The prepared schema will be a map:
        key: (swagger_path, method) e.g. ('/v1/reverse', 'GET')
        value: a SchemaMap

    For any request, you just need to:
        1) Validate {k, v for k, v in query.params} against
            request_query_schema
        2) Validate request body against request_body_schema
        3) Validate response body against response_body_schema

        Response and request bodies will need to be transformed as indicated by
        their content type (e.g. simplejson.loads if you have application/json
        type).

    :returns: SchemaAndResolver
    """
    with open(schema_path, 'r') as schema_file:
        schema = simplejson.load(schema_file)
    return SchemaAndResolver(
        request_to_schema_map=dict(build_request_to_schemas_map(schema)),
        resolver=get_model_resolver(schema),
    )
