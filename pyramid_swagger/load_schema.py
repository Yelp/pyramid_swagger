# -*- coding: utf-8 -*-
"""
Module to load swagger specs and build efficient data structures for querying
them during request validation.
"""
from collections import namedtuple

import simplejson
from jsonschema import RefResolver


def extract_query_param_schema(schema):
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
        if s['paramType'] == 'query'
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


def extract_body_schema(schema):
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
        return strip_swagger_markup(matching_body_schemas[0])
    else:
        return None


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
        for k, v in schema.iteritems()
        if k not in swagger_specific_keys
    )


def get_model_resolver(schema):
    """
    Gets the schema and a RefResolver. RefResolver's will resolve "$ref:
    ObjectType" entries in the schema, which are used to describe more complex
    objects.

    :returns: The RefResolver for the schema's models.
    :rtype: RefResolver
    """
    models = dict(
        (k, strip_swagger_markup(v))
        for k, v in schema['models'].iteritems()
    )
    return RefResolver('', '', models)


class SchemaMap(namedtuple(
        'SM', [
            'request_query_schema',
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


def build_request_to_schemas_map(schema):
    """Take the swagger schema and build a map from incoming path to a
    jsonschema for requests and responses."""
    request_to_schema = {}
    for api in schema['apis']:
        path = api['path']
        for op in api['operations']:
            key = (path, op['method'])
            request_query_schema = extract_query_param_schema(op)
            request_body_schema = extract_body_schema(op)

            model_name = op['type']
            if model_name in schema['models']:
                response_body_schema = dict(schema['models'][model_name])
            else:
                response_body_schema = {
                    "id": "default",
                    "description": "primitive type container",
                    "type": model_name,
                }

            # Now that we have the necessary info for this particular
            # path/method combination, build our dict.
            request_to_schema[key] = SchemaMap(
                request_query_schema=request_query_schema,
                request_body_schema=request_body_schema,
                response_body_schema=response_body_schema,
            )
    return request_to_schema


class SchemaAndResolver(namedtuple('SAR', ['schema_map', 'resolver'])):
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
    with open(schema_path, 'r') as f:
        schema = simplejson.load(f)
    return SchemaAndResolver(
        schema_map=build_request_to_schemas_map(schema),
        resolver=get_model_resolver(schema),
    )
