# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pyramid.interfaces import IRoutesMapper

import re

import jsonschema.exceptions
import simplejson
from jsonschema.validators import Draft3Validator, Draft4Validator
from pyramid.httpexceptions import HTTPClientError, HTTPInternalServerError
from .ingest import compile_swagger_schema
from .model import PathNotMatchedError


EXTENDED_TYPES = {
    'float': (float,),
    'int': (int,),
}

# We don't always care about validating every endpoint (e.g. static resources)
SKIP_VALIDATION_DEFAULT = [
    '/(static)\\b',
    '/(api-docs).*'
]


def validation_tween_factory(handler, registry):
    """Pyramid tween for performing request validation.

    Note this is very simple -- it validates requests and responses while
    delegating to the relevant matching view.
    """
    (
        schema_dir,
        enable_swagger_spec_validation,
        enable_response_validation,
        skip_validation
    ) = load_settings(registry)

    schema = compile_swagger_schema(schema_dir, enable_swagger_spec_validation)
    route_mapper = registry.queryUtility(IRoutesMapper)

    def validator_tween(request):
        if should_skip_validation(skip_validation, request.path):
            return handler(request)

        schema_data, resolver = find_schema_for_request(schema, request)

        _validate_request(
            route_mapper,
            request,
            schema_data,
            resolver
        )
        response = handler(request)
        if enable_response_validation:
            _validate_response(
                response,
                schema_data,
                resolver
            )

        return response

    return validator_tween


def load_settings(registry):
    # By default, assume cwd contains the swagger schemas.
    schema_dir = registry.settings.get(
        'pyramid_swagger.schema_directory',
        'api_docs/'
    )

    enable_swagger_spec_validation = registry.settings.get(
        'pyramid_swagger.enable_swagger_spec_validation',
        True
    )

    enable_response_validation = registry.settings.get(
        'pyramid_swagger.enable_response_validation',
        True
    )
    # Static URLs and /api-docs skip validation by default
    skip_validation = registry.settings.get(
        'pyramid_swagger.skip_validation',
        SKIP_VALIDATION_DEFAULT
    )
    if isinstance(skip_validation, list):
        skip_validation_res = [
            re.compile(endpoint) for endpoint in skip_validation
        ]
    else:
        skip_validation_res = [re.compile(skip_validation)]

    return (
        schema_dir,
        enable_swagger_spec_validation,
        enable_response_validation,
        skip_validation_res,
    )


def should_skip_validation(skip_validation_res, path):
    # Skip validation for the specified endpoints
    return any(r.match(path) for r in skip_validation_res)


def find_schema_for_request(schema, request):
    try:
        return schema.schema_and_resolver_for_request(request)
    except PathNotMatchedError as exc:
        raise HTTPClientError(str(exc))


def _validate_request(route_mapper, request, schema_data, resolver):
    """ Validates a request and raises an HTTPClientError on failure.

    :param request: the request object to validate
    :type request: Pyramid request object passed into a view
    :param schema_data: our mapping from request data to schemas (see
        load_schema)
    :type schema_data: dict
    :param resolver: the request object to validate
    :type resolver: Pyramid request object passed into a view
    """
    try:
        validate_incoming_request(
            route_mapper,
            request,
            schema_data,
            resolver
        )
    except jsonschema.exceptions.ValidationError as exc:
        # This will alter our stack trace slightly, but Pyramid knows how
        # to render it. And the real value is in the message anyway.
        raise HTTPClientError(str(exc))


def _validate_response(response, schema_data, schema_resolver):
    """ Validates a response and raises an HTTPInternalServerError on failure.

    :param response: the response object to validate
    :type response: Pyramid response object passed into a view
    :param schema_data: our mapping from request data to schemas (see
        load_schema)
    :type schema_data: dict
    :param resolver: the request object to validate
    :type resolver: Pyramid request object passed into a view
    """
    try:
        validate_outgoing_response(
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

    :param request_schema: request schema
    :type request_schema: dict
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


def validate_incoming_request(route_mapper, request, schema_map, resolver):
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
    if schema_map.request_query_schema:
        # You'll notice we use Draft3 some places and Draft4 in others.
        # Unfortunately this is just Swagger's inconsistency showing. It
        # may be nice in the future to do the necessary munging to make
        # everything Draft4 compatible, although the Swagger UI will
        # probably never truly support Draft4.
        request_query_params = dict(
            (k, cast_request_param(schema_map.request_query_schema, k, v))
            for k, v
            in request.GET.items()
        )
        Draft3Validator(
            schema_map.request_query_schema,
            resolver=resolver,
            types=EXTENDED_TYPES,
        ).validate(request_query_params)

    if schema_map.request_path_schema:
        # We don't have access to this yet but let's go ahead and build the
        # matchdict so we can validate it.
        info = route_mapper(request)
        matchdict = dict(
            (k, cast_request_param(schema_map.request_path_schema, k, v))
            for k, v
            in info.get('match', {}).items()
        )
        Draft3Validator(
            schema_map.request_path_schema,
            resolver=resolver,
            types=EXTENDED_TYPES,
        ).validate(matchdict)

    # Body validation
    if schema_map.request_body_schema:
        body = getattr(request, 'json_body', {})
        Draft4Validator(
            schema_map.request_body_schema,
            resolver=resolver,
            types=EXTENDED_TYPES,
        ).validate(body)


def validate_outgoing_response(response, schema_map, resolver):
    """Validates response against our schemas.

    :param response: the response object to validate
    :type response: Requests response object
    :param schema_map: our mapping from request data to schemas (see
        load_schema)
    :type schema_map: dict
    :param resolver: a resolver for validation, if any
    :type resolver: a jsonschema resolver or None
    :returns: None
    """
    body = prepare_body(response)
    # Short circuit if we are supposed to not validate anything.
    if schema_map.response_body_schema.get('type') == 'void' and body is None:
        return
    Draft4Validator(
        schema_map.response_body_schema,
        resolver=resolver,
        types=EXTENDED_TYPES,
    ).validate(body)


def prepare_body(response):
    # content_type and charset must both be set to access response.text
    if response.content_type is None or response.charset is None:
        raise HTTPInternalServerError(
            'Response validation error: Content-Type and charset must be set'
        )

    if 'application/json' in response.content_type:
        return simplejson.loads(response.text)
    else:
        return response.text
