# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

import jsonschema.exceptions
import simplejson
from jsonschema.validators import Draft3Validator, Draft4Validator
from pyramid.httpexceptions import HTTPClientError, HTTPInternalServerError

from .load_schema import load_schema


EXTENDED_TYPES = {
    'float': (float,),
    'int': (int,),
}


# We don't always care about validating every endpoint (e.g. static resources)
skip_validation_re = re.compile(r'/(static)\b')


def swagger_schema_for_request(request, schema_map):
    for (s_path, s_method), value in schema_map.items():
        if partial_path_match(request.path, s_path):
            return value


def validation_tween_factory(handler, registry):
    """Pyramid tween for performing request validation.

    Note this is very simple -- it validates requests and responses while
    delegating to the relevant matching view.
    """
    # Pre-load the schema outside our tween
    schema_resolver = load_schema(registry.settings.get(
        'pyramid_swagger.schema_path',
        'swagger.json'
    ))

    enable_response_validation = registry.settings.get(
        'pyramid_swagger.enable_response_validation',
        False
    )

    def validator_tween(request):
        schema_data = swagger_schema_for_request(
            request,
            schema_resolver.schema_map
        )

        # Bail early if we cannot find a relevant entry in the Swagger spec.
        if schema_data is None:
            raise HTTPClientError(
                'Could not find the relevant path ({0})'
                ' in the Swagger spec. Perhaps you forgot'
                ' to add it?'.format(request.path)
            )

        _validate_request(
            request,
            schema_data,
            schema_resolver.resolver
        )
        response = handler(request)
        if enable_response_validation:
            _validate_response(
                request,
                response,
                schema_data,
                schema_resolver.resolver
            )

        return response

    return validator_tween


def _validate_request(request, schema_data, resolver):
    """ Validates a request and raises an HTTPClientError on failure.

    :param request: the request object to validate
    :type request: Pyramid request object passed into a view
    :param schema_map: our mapping from request data to schemas (see
        load_schema)
    :type schema_map: dict
    :param resolver: the request object to validate
    :type resolver: Pyramid request object passed into a view
    """
    try:
        validate_incoming_request(
            request,
            schema_data,
            resolver
        )
    except jsonschema.exceptions.ValidationError as exc:
        # This will alter our stack trace slightly, but Pyramid knows how
        # to render it. And the real value is in the message anyway.
        raise HTTPClientError(str(exc))


def _validate_response(request, response, schema_data, schema_resolver):
    """ Validates a response and raises an HTTPInternalServerError on failure.

    :param request: the request object
    :type request: Pyramid request object passed into a view
    :param response: the response object to validate
    :type response: Pyramid response object passed into a view
    :param schema_map: our mapping from request data to schemas (see
        load_schema)
    :type schema_map: dict
    :param resolver: the request object to validate
    :type resolver: Pyramid request object passed into a view
    """
    try:
        validate_outgoing_response(
            request,
            response,
            schema_data,
            schema_resolver
        )
    except jsonschema.exceptions.ValidationError as exc:
        # This will alter our stack trace slightly, but Pyramid knows how
        # to render it. And the real value is in the message anyway.
        raise HTTPInternalServerError(str(exc))


def cast_request_param(request_schema, param_name, param_value):
    """Try to cast a request param (e.g. query arg, POST data) from a string to
    its specified type in the schema. This allows validating non-string params.

    :param schema_map: request schema
    :type schema_map: dict
    :param param_name: param name
    :type: string
    :param param_name: param value
    :type: string
    """
    type_to_cast_fn = {
        'integer': int,
        'float': float,
        'boolean': bool,
    }

    param_type = request_schema['properties'].get(param_name, {}).get('type')
    try:
        return type_to_cast_fn.get(param_type, lambda x: x)(param_value)
    except ValueError:
        # Ignore type error, let jsonschema validation handle incorrect types
        return param_value


def validate_incoming_request(request, schema_map, resolver):
    """Validates an incoming request against our schemas.

    :param request: the request object to validate
    :type request: Pyramid request object passed into a view
    :param schema_map: our mapping from request data to schemas (see
        load_schema)
    :type schema_map: dict
    :param resolver: the request object to validate
    :type resolver: Pyramid request object passed into a view
    :returns: None
    """
    # Static URLs are skipped
    if not skip_validation_re.match(request.path):
        if schema_map.request_query_schema:
            # You'll notice we use Draft3 some places and Draft4 in others.
            # Unfortunately this is just Swagger's inconsistency showing. It
            # may be nice in the future to do the necessary munging to make
            # everything Draft4 compatible, although the Swagger UI will
            # probably never truly support Draft4.
            request_query_params = dict(
                (k, cast_request_param(schema_map.request_query_schema, k, v))
                for k, v
                in request.params.items()
            )
            Draft3Validator(
                schema_map.request_query_schema,
                resolver=resolver,
                types=EXTENDED_TYPES,
            ).validate(request_query_params)

        if schema_map.request_path_schema:
            request_path_params = dict(
                (k, cast_request_param(schema_map.request_path_schema, k, v))
                for k, v
                in request.matchdict.items()
            )
            Draft3Validator(
                schema_map.request_path_schema,
                resolver=resolver,
                types=EXTENDED_TYPES,
            ).validate(request_path_params)

        # Body validation
        if schema_map.request_body_schema:
            body = getattr(request, 'json_body', {})
            Draft4Validator(
                schema_map.request_body_schema,
                resolver=resolver,
                types=EXTENDED_TYPES,
            ).validate(body)


def validate_outgoing_response(request, response, schema_map, resolver):
    """Validates response against our schemas.

    :param request: the request object to validate
    :type request: Pyramid request object passed into a view
    :param response: the response object to validate
    :type response: Requests response object
    :param schema_map: our mapping from request data to schemas (see
        load_schema)
    :type schema_map: dict
    :param resolver: a resolver for validation, if any
    :type resolver: a jsonschema resolver or None
    :returns: None
    """
    if not skip_validation_re.match(request.path):
        body = prepare_body(response)
        Draft4Validator(
            schema_map.response_body_schema,
            resolver=resolver,
            types=EXTENDED_TYPES,
        ).validate(body)


def prepare_body(response):
    if 'application/json; charset=UTF-8' in response.headers.values():
        return simplejson.loads(response.content)
    else:
        return response.content


def partial_path_match(p1, p2, kwarg_re=r'\{.*\}'):
    """Validates if p1 and p2 matches, ignoring any kwargs in the string.

    We need this to ensure we can match Swagger patterns like:
        /foo/{id}
    against the observed pyramid path
        /foo/1

    :param p1: path of a url
    :type p1: string
    :param p2: path of a url
    :type p2: string
    :param kwarg_re: regex pattern to identify kwargs
    :type kwarg_re: regex string
    :returns: boolean
    """
    split_p1 = p1.split('/')
    split_p2 = p2.split('/')
    pat = re.compile(kwarg_re)
    if len(split_p1) != len(split_p2):
        return False
    for pos, (partial_p1, partial_p2) in enumerate(zip(split_p1, split_p2)):
        if pat.match(partial_p1) or pat.match(partial_p2):
            continue
        if not partial_p1 == partial_p2:
            return False
    return True
