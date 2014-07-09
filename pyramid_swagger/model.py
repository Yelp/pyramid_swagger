"""
The core model we use to represent the entire ingested swagger schema for this
service.
"""
import re

from .ingest import ingest_schema_files
from pyramid.httpexceptions import HTTPClientError


class SwaggerSchema(object):
    """
    This object contains the relevant logic for ingesting as series of
    swagger-compliant files and exposes methods for efficiently checking
    json objects against their schemas.
    """

    def __init__(self, schema_dir, enable_swagger_spec_validation):
        self.schema_resolvers = ingest_schema_files(
            schema_dir,
            enable_swagger_spec_validation
        )

    def schema_and_resolver_for_request(self, request):
        """Takes a request and returns the relevant schema, ready for
        validation.

        :returns: (schema_map, resolver) for this particular request.
        """
        for schema_resolver in self.schema_resolvers:
            schema_map = schema_resolver.schema_map
            resolver = schema_resolver.resolver
            for (s_path, s_method), value in schema_map.items():
                if (
                        partial_path_match(request.path, s_path) and
                        (s_method == request.method)
                ):
                    return (value, resolver)

        raise HTTPClientError(
            'Could not find the relevant path ({0}) '
            'in the Swagger spec. Perhaps you forgot '
            'to add it?'.format(request.path)
        )


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
