# -*- coding: utf-8 -*-
"""
Module for automatically serving /api-docs* via Pyramid.
"""
import copy
import os.path

import simplejson
import yaml


from bravado_core.spec import strip_xscope
from jsonschema import RefResolutionError
from six.moves.urllib.parse import urlparse, urlunparse
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


def dereference_definition(spec, url, current_file, definitions_dict):
    """
    Dereference a given definition (by URL) updating the definitions
    dictionary and fetching all the related objects
    :param spec:
    :param url: url of the reference to be extracted
    :param current_file: base file used for relative url resolution
    :param definitions_dict: dictionary containing all the definitions
    :return: python object containing the model representation specified in url
    """

    def _translate_definition_target(target, prefix='', separator='|'):
        """
        Translate the definition target to a consistent way
        which does not uses the '#' for the name definition
        :param target: original definition target
        :param prefix: prefix used if no file were specified on the target
        :param separator: separator character to be used instead of '#'
        :return: the converted target (it will be the new name of the link)
        """
        value = target.replace("#/definitions/", separator)
        if value.split(separator)[0] == '':
            value = prefix + value
        return value

    reference_value = _translate_definition_target(url)
    if reference_value not in definitions_dict:
        try:
            with spec.resolver.resolving(url) as resolved_spec_dict:
                spec_dict = copy.deepcopy(resolved_spec_dict)
        except RefResolutionError:
            with spec.resolver.resolving(current_file + url) \
                    as resolved_spec_dict:
                spec_dict = copy.deepcopy(resolved_spec_dict)
        definitions_dict[reference_value] = spec_dict
        _resolve_refs(spec, spec_dict, definitions_dict,
                      current_file=url.split('#')[0])
    return reference_value


def resolve_ref(spec, url, definitions_dict, current_file):
    with spec.resolver.resolving(url) as resolved_spec_dict:
        spec_dict = copy.deepcopy(resolved_spec_dict)
        return _resolve_refs(spec, spec_dict, definitions_dict, current_file)


def _resolve_refs(spec, val, definitions_dict, current_file=''):
    if isinstance(val, dict):
        new_dict = {}
        for key, subval in val.items():
            if key == '$ref':
                # assume $ref is the only key in the dict
                if "#/definitions/" in subval:
                    # Update the reference target
                    val[key] = "#/definitions/{reference_value}".format(
                        reference_value=dereference_definition(
                            spec, subval, current_file, definitions_dict),
                    )
                    return val
                else:
                    return resolve_ref(spec, subval, definitions_dict,
                                       current_file=subval.split('#')[0])
            else:
                new_dict[key] = _resolve_refs(
                    spec, subval, definitions_dict, current_file)
        return new_dict

    if isinstance(val, list):
        for index, subval in enumerate(val):
            val[index] = _resolve_refs(
                spec, subval, definitions_dict, current_file)
    return val


def resolve_refs(spec, val, current_file=''):
    """
    Resolve all the needed references for a staring object
    :param spec:
    :param val: not dereferences swagger object
    :param current_file: base file for the swagger spec
    :return: a self-containing swagger specification object

    NOTE: internal references are still possible
    """

    # Create the definitions dictionary and mark the method to join the
    # definitions on the resulting object
    definitions_dict = {}

    result = _resolve_refs(spec, val, definitions_dict, current_file)

    # join definitions and resulting object (NOTE: to be executed only on the
    # top level object)
    result['definitions'] = definitions_dict

    return result


class NodeWalker(object):
    def __init__(self):
        pass

    def walk(self, item, *args, **kwargs):
        dupe = copy.deepcopy(item)
        return self._walk(dupe, *args, **kwargs)

    def _walk(self, item, *args, **kwargs):
        if isinstance(item, list):
            return self._walk_list(item, *args, **kwargs)

        elif isinstance(item, dict):
            return self._walk_dict(item, *args, **kwargs)

        else:
            return self._walk_item(item, *args, **kwargs)

    def _walk_list(self, item, *args, **kwargs):
        for index, subitem in enumerate(item):
            item[index] = self._walk(subitem, *args, **kwargs)
        return item

    def _walk_dict(self, item, *args, **kwargs):
        for key, value in item.items():
            item[key] = self._walk_dict_item(key, value, *args, **kwargs)
        return item

    def _walk_dict_item(self, key, value, *args, **kwargs):
        return self._walk(value, *args, **kwargs)

    def _walk_item(self, value, *args, **kwargs):
        return value


def get_path_if_relative(url):
    parts = urlparse(url)

    if parts.scheme or parts.netloc:
        # only rewrite relative paths
        return

    if not parts.path:
        # don't rewrite internal refs
        return

    if parts.path.startswith('/'):
        # don't rewrite absolute refs
        return

    return parts


class NodeWalkerForRefFiles(NodeWalker):
    def walk(self, spec):
        all_refs = []

        spec_fname = spec.origin_url
        if spec_fname.startswith('file://'):
            spec_fname = spec_fname.replace('file://', '')
        spec_dirname = os.path.dirname(spec_fname)

        parent = super(NodeWalkerForRefFiles, self)
        parent.walk(spec.client_spec_dict, spec, spec_dirname, all_refs)

        all_refs = [os.path.relpath(f, spec_dirname) for f in all_refs]
        all_refs = set(all_refs)

        core_dirname, core_fname = os.path.split(spec_fname)
        all_refs.add(core_fname)

        return all_refs

    def _walk_dict_item(self, key, value, spec, dirname, all_refs):
        if key != '$ref':
            parent = super(NodeWalkerForRefFiles, self)
            return parent._walk_dict_item(key, value, spec, dirname, all_refs)

        # assume $ref is the only key in the dict
        parts = get_path_if_relative(value)
        if not parts:
            return value

        full_fname = os.path.join(dirname, parts.path)
        norm_fname = os.path.normpath(full_fname)
        all_refs.append(norm_fname)

        with spec.resolver.resolving(value) as spec_dict:
            dupe = copy.deepcopy(spec_dict)
            self._walk(dupe, spec, os.path.dirname(norm_fname), all_refs)


class NodeWalkerForCleaningRefs(NodeWalker):
    def walk(self, item, schema_format):
        parent = super(NodeWalkerForCleaningRefs, self)
        return parent.walk(item, schema_format)

    @staticmethod
    def fix_ref(ref, schema_format):
        parts = get_path_if_relative(ref)
        if not parts:
            return

        path, ext = os.path.splitext(parts.path)
        return urlunparse([
            parts.scheme,
            parts.netloc,
            '{0}.{1}'.format(path, schema_format),
            parts.params,
            parts.query,
            parts.fragment,
        ])

    def _walk_dict_item(self, key, value, schema_format):
        if key != '$ref':
            parent = super(NodeWalkerForCleaningRefs, self)
            return parent._walk_dict_item(key, value, schema_format)

        return self.fix_ref(value, schema_format) or value


class YamlRendererFactory(object):
    def __init__(self, info):
        pass

    def __call__(self, value, system):
        response = system['request'].response
        response.headers['Content-Type'] = 'application/x-yaml; charset=UTF-8'
        return yaml.dump(value).encode('utf-8')


def build_swagger_20_swagger_schema_views(config):
    settings = config.registry.settings
    if settings.get('pyramid_swagger.dereference_served_schema'):
        views = _build_dereferenced_swagger_20_schema_views(config)
    else:
        views = _build_swagger_20_schema_views(config)
    return views


def _build_dereferenced_swagger_20_schema_views(config):
    def view_for_swagger_schema(request):
        settings = config.registry.settings
        resolved_dict = settings.get('pyramid_swagger.schema20_resolved')
        if not resolved_dict:
            spec = settings['pyramid_swagger.schema20']
            spec_copy = copy.deepcopy(spec.client_spec_dict)
            resolved_dict = strip_xscope(resolve_refs(spec, spec_copy))
            settings['pyramid_swagger.schema20_resolved'] = resolved_dict
        return resolved_dict

    for schema_format in ['yaml', 'json']:
        route_name = 'pyramid_swagger.swagger20.api_docs.{0}'\
            .format(schema_format)
        yield PyramidEndpoint(
            path='/swagger.{0}'.format(schema_format),
            view=view_for_swagger_schema,
            route_name=route_name,
            renderer=schema_format,
        )


def _build_swagger_20_schema_views(config):
    spec = config.registry.settings['pyramid_swagger.schema20']

    walker = NodeWalkerForRefFiles()
    all_files = walker.walk(spec)

    file_map = {}

    def view_for_swagger_schema(request):
        path, ext = os.path.splitext(request.path)
        ext = ext.lstrip('.')
        actual_fname = file_map[request.path]
        with spec.resolver.resolving(actual_fname) as spec_dict:
            clean_response = strip_xscope(spec_dict)
            ref_walker = NodeWalkerForCleaningRefs()
            fixed_spec = ref_walker.walk(clean_response, ext)
            return fixed_spec

    for ref_fname in all_files:
        ref_fname_parts = os.path.splitext(ref_fname)
        for schema_format in ['yaml', 'json']:
            route_name = 'pyramid_swagger.swagger20.api_docs.{0}.{1}'\
                .format(ref_fname.replace('/', '.'), schema_format)
            path = '/{0}.{1}'.format(ref_fname_parts[0], schema_format)
            file_map[path] = ref_fname
            yield PyramidEndpoint(
                path=path,
                route_name=route_name,
                view=view_for_swagger_schema,
                renderer=schema_format,
            )
