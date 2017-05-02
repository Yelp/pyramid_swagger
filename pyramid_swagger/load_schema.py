# -*- coding: utf-8 -*-
"""
Module to load swagger specs and build efficient data structures for querying
them during request validation.
"""
from __future__ import unicode_literals

from collections import namedtuple

import simplejson
from jsonschema import _validators
from jsonschema import RefResolver
from jsonschema import validators
from jsonschema.exceptions import ValidationError
from jsonschema.validators import Draft3Validator
from jsonschema.validators import Draft4Validator

from pyramid_swagger.model import partial_path_match


EXTENDED_TYPES = {
    'number': (float,),
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
    properties = filter_params_by_type(schema, param_type)
    if not properties:
        return

    # Generate a jsonschema that describes the set of all query parameters. We
    # can then validate this against dict(request.params).
    return {
        'type': 'object',
        'properties': dict((p['name'], p) for p in properties),
        # Allow extra headers. Most HTTP requests will have headers which
        # are outside the scope of the spec (like `Host`, or `User-Agent`)
        'additionalProperties': param_type == 'header',
    }


def filter_params_by_type(schema, param_type):
    return [s for s in schema['parameters'] if s['paramType'] == param_type]


def extract_body_schema(schema):
    """Return the body parameter schema from an operation schema."""
    matching_body_schemas = filter_params_by_type(schema, 'body')
    # There can be only one body param
    return matching_body_schemas[0] if matching_body_schemas else None


def ignore(_validator, *args):
    """A validator which performs no validation. Used to `ignore` some schema
    fields during validation.
    """
    return


def build_swagger_type_validator(models):
    def swagger_type_validator(validator, ref, instance, schema):
        func = _validators.ref if ref in models else _validators.type_draft4
        return func(validator, ref, instance, schema)

    return swagger_type_validator


def type_validator(validator, types, instance, schema):
    """Swagger 1.2 supports parameters of 'type': 'File'. Skip validation of
    the 'type' field in this case.
    """
    if schema.get('type') == 'File':
        return []
    return _validators.type_draft3(validator, types, instance, schema)


def required_validator(validator, req, instance, schema):
    """Swagger 1.2 expects `required` to be a bool in the Parameter object, but
    a list of properties in a Model object.
    """
    if schema.get('paramType'):
        if req is True and not instance:
            return [ValidationError("%s is required" % schema['name'])]
        return []
    return _validators.required_draft4(validator, req, instance, schema)


def get_body_validator(models):
    """Returns a validator for the request body, based on a
    :class:`jsonschema.validators.Draft4Validator`, with extra validations
    added for swaggers extensions to jsonschema.

    :param models: a mapping of reference to models
    :returns: a :class:`jsonschema.validators.Validator` which can validate
        the request body.
    """
    return validators.extend(
        Draft4Validator,
        {
            'paramType': ignore,
            'name': ignore,
            'type': build_swagger_type_validator(models),
            'required': required_validator,
        }
    )


Swagger12ParamValidator = validators.extend(
    Draft3Validator,
    {
        'paramType': ignore,
        'name': ignore,
        'type': type_validator,
    }
)


class ValidatorMap(
    namedtuple('_VMap', 'query path form headers body response')
):
    """
    A data object with validators for each part of the request and response
    objects. Each field is a :class:`SchemaValidator`.
    """
    __slots__ = ()

    @classmethod
    def from_operation(cls, operation, models, resolver):
        args = []
        for schema, validator in [
            (build_param_schema(operation, 'query'), Swagger12ParamValidator),
            (build_param_schema(operation, 'path'), Swagger12ParamValidator),
            (build_param_schema(operation, 'form'), Swagger12ParamValidator),
            (build_param_schema(operation, 'header'), Swagger12ParamValidator),
            (extract_body_schema(operation), get_body_validator(models)),
            (extract_response_body_schema(operation, models),
                Draft4Validator),
        ]:
            args.append(SchemaValidator.from_schema(
                schema,
                resolver,
                validator))

        return cls(*args)


class SchemaValidator(object):
    """A Validator used by :mod:`pyramid_swagger.tween` to validate a
    field from the request or response.

    :param schema: a :class:`dict` jsonschema that was used by the
        validator
    :param valdiator: a Validator which a func:`validate` method
        for validating a field from a request or response. This
        will often be a :class:`jsonschema.validator.Validator`.
    """

    def __init__(self, schema, validator):
        self.schema = schema
        self.validator = validator

    @classmethod
    def from_schema(cls, schema, resolver, validator_class):
        return cls(
            schema,
            validator_class(schema, resolver=resolver, types=EXTENDED_TYPES))

    def validate(self, values):
        """Validate a :class:`dict` of values. If `self.schema` is falsy this
        is a noop.
        """
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
            partial_path_match(request.path_info, self.path) and
            request.method == self.method
        )


def extract_response_body_schema(operation, schema_models):
    if operation['type'] in schema_models:
        return extract_validatable_type(operation['type'], schema_models)

    acceptable_fields = (
        'type', '$ref', 'format', 'defaultValue', 'enum', 'minimum',
        'maximum', 'items', 'uniqueItems'
    )

    return dict(
        (field, operation[field])
        for field in acceptable_fields
        if field in operation
    )


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
    resolver = RefResolver('', '', schema.get('models', {}))
    return build_request_to_validator_map(schema, resolver)
