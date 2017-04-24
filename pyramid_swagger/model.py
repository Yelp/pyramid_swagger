# -*- coding: utf-8 -*-
"""
The core model we use to represent the entire ingested swagger schema for this
service.
"""
import re
from collections import namedtuple


PyramidEndpoint = namedtuple(
    'PyramidEndpoint',
    'path route_name view renderer')


class PathNotMatchedError(Exception):
    """Raised when a SwaggerSchema object is given a request it cannot match
    against its stored schema."""
    pass


class SwaggerSchema(object):
    """
    This object contains data structures representing your Swagger schema
    and exposes methods for efficiently finding the relevant schemas for a
    Pyramid request.

    :param pyramid_endpoints: a list of :class:`PyramidEndpoint` which define
        the pyramid endpoints to create for serving the api docs
    :param resource_validators: a list of resolvers, one per Swagger resource
    :type resource_validators: list of mappings from :class:`RequestMatcher`
        to :class:`ValidatorMap`
    for every operation in the api specification.
    """

    def __init__(self, pyramid_endpoints, resource_validators):
        self.pyramid_endpoints = pyramid_endpoints
        self.resource_validators = resource_validators

    def validators_for_request(self, request, **kwargs):
        """Takes a request and returns a validator mapping for the request.

        :param request: A Pyramid request to fetch schemas for
        :type request: :class:`pyramid.request.Request`
        :returns: a :class:`pyramid_swagger.load_schema.ValidatorMap` which can
            be used to validate `request`
        """
        for resource_validator in self.resource_validators:
            for matcher, validator_map in resource_validator.items():
                if matcher.matches(request):
                    return validator_map

        raise PathNotMatchedError(
            'Could not find the relevant path ({0}) in the Swagger schema. '
            'Perhaps you forgot to add it?'.format(request.path_info)
        )

    def get_api_doc_endpoints(self):
        return self.pyramid_endpoints


def partial_path_match(path1, path2, kwarg_re=r'\{.*\}'):
    """Validates if path1 and path2 matches, ignoring any kwargs in the string.

    We need this to ensure we can match Swagger patterns like:
        /foo/{id}
    against the observed pyramid path
        /foo/1

    :param path1: path of a url
    :type path1: string
    :param path2: path of a url
    :type path2: string
    :param kwarg_re: regex pattern to identify kwargs
    :type kwarg_re: regex string
    :returns: boolean
    """
    split_p1 = path1.split('/')
    split_p2 = path2.split('/')
    pat = re.compile(kwarg_re)
    if len(split_p1) != len(split_p2):
        return False
    for partial_p1, partial_p2 in zip(split_p1, split_p2):
        if pat.match(partial_p1) or pat.match(partial_p2):
            continue
        if not partial_p1 == partial_p2:
            return False
    return True
