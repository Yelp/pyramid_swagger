# -*- coding: utf-8 -*-
"""
Module for automatically serving /api-docs* via Pyramid.
"""
import copy
import hashlib
import os.path
import simplejson
import yaml

from pyramid_swagger.model import PyramidEndpoint


# TODO: document that this is now a public interface
def register_api_doc_endpoints(config, endpoints, base_path='/api-docs'):
    """Create and register pyramid endpoints to service swagger api docs.
    Routes and views will be registered on the `config` at `path`.

    :param config: a pyramid configuration to register the new views and routes
    :type  config: :class:`pyramid.config.Configurator`
    :param endpoints: a list of endpoints to register as routes and views
    :type  endpoints: a list of :class:`pyramid_swagger.model.PyramidEndpoint`
    :param base_path: the base path used to register api doc endpoints.
        Defaults to `/api-docs`.
    :type  base_path: string
    """
    for endpoint in endpoints:
        path = base_path.rstrip('/') + endpoint.path
        config.add_route(endpoint.route_name, path)
        config.add_view(
            endpoint.view,
            route_name=endpoint.route_name,
            renderer=endpoint.renderer)


def build_swagger_12_endpoints(resource_listing, api_declarations):
    """
    :param resource_listing: JSON representing a Swagger 1.2 resource listing
    :type resource_listing: dict
    :param api_declarations: JSON representing Swagger 1.2 api declarations
    :type api_declarations: dict
    :rtype: iterable of :class:`pyramid_swagger.model.PyramidEndpoint`
    """
    yield build_swagger_12_resource_listing(resource_listing)

    for name, filepath in api_declarations.items():
        with open(filepath) as input_file:
            yield build_swagger_12_api_declaration(
                name, simplejson.load(input_file))


def build_swagger_12_resource_listing(resource_listing):
    """
    :param resource_listing: JSON representing a Swagger 1.2 resource listing
    :type resource_listing: dict
    :rtype: :class:`pyramid_swagger.model.PyramidEndpoint`
    """
    def view_for_resource_listing(request):
        # Thanks to the magic of closures, this means we gracefully return JSON
        # without file IO at request time.
        return resource_listing

    return PyramidEndpoint(
        path='',
        route_name='pyramid_swagger.swagger12.api_docs',
        view=view_for_resource_listing,
        renderer='json')


def build_swagger_12_api_declaration(resource_name, api_declaration):
    """
    :param resource_name: The `path` parameter from the resource listing for
        this resource.
    :type resource_name: string
    :param api_declaration: JSON representing a Swagger 1.2 api declaration
    :type api_declaration: dict
    :rtype: :class:`pyramid_swagger.model.PyramidEndpoint`
    """
    # NOTE: This means our resource paths are currently constrained to be valid
    # pyramid routes! (minus the leading /)
    route_name = 'pyramid_swagger.swagger12.apidocs-{0}'.format(resource_name)
    return PyramidEndpoint(
        path='/{0}'.format(resource_name),
        route_name=route_name,
        view=build_swagger_12_api_declaration_view(api_declaration),
        renderer='json')


def build_swagger_12_api_declaration_view(api_declaration_json):
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


class RefResolver(object):
    def __init__(self, spec):
        self.spec = spec
        self.origin_url = spec.origin_url

        self.definitions = {}
        self.defs_to_uuids = {}

    def resolve(self):
        spec_copy = copy.deepcopy(self.spec.client_spec_dict)
        resolved_spec = self._resolve_refs(spec_copy)
        if self.definitions:
            resolved_spec['definitions'] = self.definitions
        return resolved_spec

    def _create_key(self, abs_path):
        common = os.path.commonprefix([
            self.origin_url,
            abs_path,
        ])
        unique_path = abs_path.replace(common, '')
        m = hashlib.md5()
        m.update(unique_path.encode('utf-8'))
        key = m.hexdigest()

        return key

    def _resolve_ref(self, url):
        with self.spec.resolver.resolving(url):
            abs_path, spec_dict = self.spec.resolver.resolve(url)
            if abs_path.startswith(self.origin_url):
                # if it's internal to the original, don't resolve
                return {'$ref': url}

            key = self.defs_to_uuids.get(abs_path)
            if not key:
                key = self._create_key(abs_path)
                self.defs_to_uuids[abs_path] = key

                spec_dict = copy.deepcopy(spec_dict)
                resolved = self._resolve_refs(spec_dict)

                self.definitions[key] = resolved

            return {'$ref': '#/definitions/%s' % key}

    def _resolve_refs(self, val):
        if isinstance(val, dict):
            new_dict = {}
            for key, subval in val.items():
                if key == '$ref':
                    # assume $ref is the only key in the dict
                    return self._resolve_ref(subval)
                else:
                    new_dict[key] = self._resolve_refs(subval)
            return new_dict

        if isinstance(val, list):
            for index, subval in enumerate(val):
                val[index] = self._resolve_refs(subval)

        return val


class YamlRendererFactory(object):
    def __init__(self, info):
        pass

    def __call__(self, value, system):
        response = system['request'].response
        response.headers['Content-Type'] = 'application/x-yaml; charset=UTF-8'
        return yaml.dump(value).encode('utf-8')


def build_swagger_20_swagger_schema_views(config):
    def view_for_swagger_schema(request):
        settings = config.registry.settings
        resolved_dict = settings.get('pyramid_swagger.schema20_resolved')
        if not resolved_dict:
            spec = settings['pyramid_swagger.schema20']
            resolver = RefResolver(spec)
            resolved_dict = resolver.resolve()
            settings['pyramid_swagger.schema20_resolved'] = resolved_dict
        return resolved_dict

    yield PyramidEndpoint(
        path='/swagger.json',
        route_name='pyramid_swagger.swagger20.api_docs.json',
        view=view_for_swagger_schema,
        renderer='json',
    )

    yield PyramidEndpoint(
        path='/swagger.yaml',
        route_name='pyramid_swagger.swagger20.api_docs.yaml',
        view=view_for_swagger_schema,
        renderer='yaml',
    )
