# -*- coding: utf-8 -*-
"""
Module for automatically serving /api-docs* via Pyramid.
"""
import simplejson


def register_api_doc_endpoints(config):
    """Create and register pyramid endpoints for /api-docs*."""
    swagger_schema = config.registry.settings['pyramid_swagger.schema']
    register_resource_listing(config, swagger_schema.resource_listing)

    for name, filepath in swagger_schema.api_declarations.items():
        with open(filepath) as input_file:
            register_api_declaration(
                config,
                name,
                simplejson.load(input_file)
            )


def register_resource_listing(config, resource_listing):
    """Registers the endpoint /api-docs.

    :param config: Configurator instance for our webapp
    :type config: pyramid Configurator
    :param resource_listing: JSON representing a resource listing
    :type resource_listing: dict
    """
    def view_for_resource_listing(request):
        # Thanks to the magic of closures, this means we gracefully return JSON
        # without file IO at request time.
        return resource_listing

    route_name = 'api_docs'
    config.add_route(route_name, '/api-docs')
    config.add_view(
        view_for_resource_listing,
        route_name=route_name,
        renderer='json'
    )


def register_api_declaration(config, resource_name, api_declaration):
    """Registers an endpoint at /api-docs.

    :param config: Configurator instance for our webapp
    :type config: pyramid Configurator
    :param resource_name: The `path` parameter from the resource listing for
        this resource.
    :type resource_name: string
    :param api_declaration: JSON representing an api declaration
    :type api_declaration: dict
    """
    # NOTE: This means our resource paths are currently constrained to be valid
    # pyramid routes! (minus the leading /)
    route_name = 'apidocs-{0}'.format(resource_name)
    config.add_route(route_name, '/api-docs/{0}'.format(resource_name))
    config.add_view(
        build_api_declaration_view(api_declaration),
        route_name=route_name,
        renderer='json'
    )


def build_api_declaration_view(api_declaration_json):
    """Thanks to the magic of closures, this means we gracefully return JSON
    without file IO at request time.
    """
    def view_for_api_declaration(request):
        # Note that we rewrite basePath to always point at this server's root.
        return dict(
            api_declaration_json,
            basePath=str(request.application_url),
        )
    return view_for_api_declaration
