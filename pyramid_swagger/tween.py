# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pyramid.interfaces import IRoutesMapper

from collections import namedtuple
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

DEFAULT_EXCLUDED_PATHS = [
    r'^/static/?',
    r'^/api-docs/?'
]


class Settings(namedtuple(
    'Settings',
    [
        'schema_dir',
        'validate_swagger_spec',
        'validate_request',
        'validate_response',
        'validate_path',
        'exclude_paths',
    ]
)):

    """A settings object for configuratble options.

    :param schema_dir: location of Swagger schema files.
    :param validate_swagger_spec: check Swagger files for correctness.
    :param validate_request: check requests against Swagger spec.
    :param validate_response: check responses against Swagger spec.
    :param validate_path: check if request path is in schema. If disabled
        and path not found in schema, request / response validation is skipped.
    :param exclude_paths: list of paths (in regex format) that should be
        excluded from validation.
    :rtype: namedtuple
    """


def validation_tween_factory(handler, registry):
    """Pyramid tween for performing validation.

    Note this is very simple -- it validates requests, responses, and paths
    while delegating to the relevant matching view.
    """
    settings = load_settings(registry)
    schema = compile_swagger_schema(
        settings.schema_dir,
        settings.validate_swagger_spec
    )
    route_mapper = registry.queryUtility(IRoutesMapper)
    disable_all_validation = not any((
        settings.validate_request,
        settings.validate_response,
        settings.validate_path
    ))

    def validator_tween(request):
        if disable_all_validation or \
                should_exclude_path(settings.exclude_paths, request.path):
            return handler(request)

        try:
            schema_data, resolver = schema.schema_and_resolver_for_request(
                request)
        except PathNotMatchedError as exc:
            if settings.validate_path:
                raise HTTPClientError(str(exc))
            else:
                return handler(request)

        if settings.validate_request:
            _validate_request(
                route_mapper,
                request,
                schema_data,
                resolver
            )

        response = handler(request)

        if settings.validate_response:
            _validate_response(
                response,
                schema_data,
                resolver
            )

        return response

    return validator_tween


def load_settings(registry):
    return Settings(
        # By default, assume cwd contains the swagger schemas.
        schema_dir=registry.settings.get(
            'pyramid_swagger.schema_directory',
            'api_docs/'
        ),
        validate_swagger_spec=registry.settings.get(
            'pyramid_swagger.enable_swagger_spec_validation',
            True
        ),
        validate_request=registry.settings.get(
            'pyramid_swagger.enable_request_validation',
            True
        ),
        validate_response=registry.settings.get(
            'pyramid_swagger.enable_response_validation',
            True
        ),
        validate_path=registry.settings.get(
            'pyramid_swagger.enable_path_validation',
            True
        ),
        exclude_paths=get_exclude_paths(registry),
    )


def get_exclude_paths(registry):
    """Compiles a list of paths that should not be validated against.
        :rtype: list of compiled validation regexes
    """
    # TODO(#63): remove deprecated `skip_validation` setting in v2.0.
    regexes = registry.settings.get(
        'pyramid_swagger.skip_validation',
        registry.settings.get(
            'pyramid_swagger.exclude_paths',
            DEFAULT_EXCLUDED_PATHS
        )
    )

    # being nice to users using strings :p
    if not isinstance(regexes, list) and not isinstance(regexes, tuple):
        regexes = [regexes]

    return [re.compile(r) for r in regexes]


def should_exclude_path(exclude_path_regexes, path):
    # Skip validation for the specified endpoints
    return any(r.match(path) for r in exclude_path_regexes)


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
        # to render it and the real value is in the message anyway.
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
