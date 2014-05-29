# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

import jsonschema.exceptions
import simplejson
from jsonschema.validators import Draft3Validator
from jsonschema.validators import Draft4Validator
from pyramid.httpexceptions import HTTPClientError

from .load_schema import load_schema


EXTENDED_TYPES = {
    'float': (float,),
    'int': (int,),
}


# We don't always care about validating every endpoint (e.g. static resources)
skip_validation_re = re.compile(r'/(static)\b')


def extract_relevant_schema(request, schema_resolver):
    for (s_path, s_method), value in schema_resolver.schema_map.items():
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

    def validator_tween(request):
        schema_data = extract_relevant_schema(request, schema_resolver)

        # Bail early if we cannot find a relevant entry in the Swagger spec.
        if schema_data is None:
            raise HTTPClientError(
                'Could not find the relevant path (%s) '
                'in the Swagger spec. Perhaps you forgot'
                'to add it?'.format(request.path)
            )

        # If we found a matching entry, validate the request against it.
        try:
            validate_incoming_request(
                request,
                schema_data,
                schema_resolver.resolver
            )
            return handler(request)
        except jsonschema.exceptions.ValidationError as exc:
            # This will alter our stack trace slightly, but Pyramid knows how
            # to render it. And the real value is in the message anyway.
            raise HTTPClientError(str(exc))

    return validator_tween


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
            Draft3Validator(
                schema_map.request_query_schema,
                resolver=resolver,
                types=EXTENDED_TYPES,
            ).validate(dict(request.params))

        # Body validation
        if schema_map.request_body_schema:
            body = getattr(request, 'json_body', None)
            Draft3Validator(
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

    :param p1: path of a url
    :type p1: string
    :param p2: path of a url
    :type p2: string
    :param kwarg_re: regex pattern to identify kwargs
    :type kwarg_re: regex string
    :returns: boolean
    """
    splitted_p1 = p1.split('/')
    splitted_p2 = p2.split('/')
    pat = re.compile(kwarg_re)
    if len(splitted_p1) != len(splitted_p2):
        return False
    for pos, partial_path in enumerate(splitted_p1):
        if pat.match(partial_path) or pat.match(splitted_p2[pos]):
            continue
        if not partial_path == splitted_p2[pos]:
            return False
    return True
