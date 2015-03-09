# -*- coding: utf-8 -*-
"""
Module to load swagger specs and build efficient data structures for querying
them during request validation.
"""
from __future__ import unicode_literals
from collections import namedtuple

import simplejson
from jsonschema import RefResolver
from jsonschema.validators import Draft3Validator, Draft4Validator

from pyramid_swagger.model import partial_path_match


EXTENDED_TYPES = {
    'float': (float,),
    'int': (int,),
}


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
            # Allow extra headers
            'additionalProperties': param_type == 'header',
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


class ValidatorMap(namedtuple('_VMap', 'query path headers body response')):
    """
    A data object with validators for each part of the request and response
    objects. Each field is a :class:`SchemaValidator`.
    """
    __slots__ = ()

    @classmethod
    def from_operation(cls, operation, models, resolver):
        args = []
        for schema, validator in [
            (build_param_schema(operation, 'query'), Draft3Validator),
            (build_param_schema(operation, 'path'), Draft3Validator),
            (build_param_schema(operation, 'header'), Draft3Validator),
            (extract_body_schema(operation, models), Draft4Validator),
            (extract_response_body_schema(operation, models),
                Draft4Validator),
        ]:
            args.append(SchemaValidator.from_schema(
                schema,
                resolver,
                validator))

        return cls(*args)


class SchemaValidator(object):

    def __init__(self, schema, validator):
        self.schema = schema
        self.validator = validator

    @classmethod
    def from_schema(cls, schema, resolver, validator_class):
        return cls(
            schema,
            validator_class(schema, resolver=resolver, types=EXTENDED_TYPES))

    def validate(self, values):
        if not self.schema:
            return
        self.validator.validate(values)


def build_request_to_validator_map(schema, resolver):
    """Build a mapping from :class:`RequestMatcher` to :class:`ValidatorMap`
    for each operation in the API spec. This mapping may be used to retrieve
    the appropriate validators for a request.
    """
    schema_models = schema.get('models', {})
    return dict(
        (
            RequestMatcher(api['path'], operation['method']),
            ValidatorMap.from_operation(operation, schema_models, resolver)
        )
        for api in schema['apis']
        for operation in api['operations']
    )


class RequestMatcher(object):
    """Match a :class:`pyramid.request.Request` to a swagger Operation"""

    def __init__(self, path, method):
        self.path = path
        self.method = method

    def matches(self, request):
        """
        :param request: a :class:`pyramid.request.Request`
        :returns: True if this matcher matches the request, False otherwise
        """
        return (
            partial_path_match(request.path, self.path) and
            request.method == self.method
        )


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


def load_schema(schema_path):
    """Prepare the api specification for request and response validation.

    :returns: a mapping from :class:`RequestMatcher` to :class:`ValidatorMap`
        for every operation in the api specification.
    :rtype: dict
    """
    with open(schema_path, 'r') as schema_file:
        schema = simplejson.load(schema_file)
    return build_request_to_validator_map(schema, get_model_resolver(schema))
