"""
The core model we use to represent the entire ingested swagger schema for this
service.
"""
import re


class PathNotMatchedError(Exception):
    """Raised when a SwaggerSchema object is given a request it cannot match
    against its stored schema."""
    pass


class SwaggerSchema(object):
    """
    This object contains data structures representing your Swagger schema
    and exposes methods for efficiently finding the relevant schemas for a
    Pyramid request.
    """

    def __init__(self, resource_listing, api_declarations, schema_resolvers):
        """Store schema_resolvers for later use.

        :param resource_listing: Filepath to a resource listing
        :type resource_listing: string
        :param api_declarations: Map from resource name to filepath of its api
            declaration
        :type api_declarations: dict
        :param schema_resolvers: a list of resolvers, one per Swagger resource
        :type schema_resolvers: list of
            pyramid_swagger.load_schema.SchemaAndResolver objects
        """
        self.resource_listing = resource_listing
        self.api_declarations = api_declarations
        self.schema_resolvers = schema_resolvers

    def schema_and_resolver_for_request(self, request):
        """Takes a request and returns the relevant schema, ready for
        validation.

        :param request: A Pyramid request to fetch schemas for
        :type request: pyramid.request.Request
        :returns: (schema_map, resolver) for this particular request.
        :rtype: A tuple of (load_schema.SchemaMap, jsonschema.Resolver)
        """
        for schema_resolver in self.schema_resolvers:
            request_to_schema_map = schema_resolver.request_to_schema_map
            resolver = schema_resolver.resolver
            for (path, method), schema_map in request_to_schema_map.items():
                if (
                        partial_path_match(request.path, path) and
                        (method == request.method)
                ):
                    return (schema_map, resolver)

        raise PathNotMatchedError(
            'Could not find the relevant path ({0}) '
            'in the Swagger schema. Perhaps you forgot '
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
