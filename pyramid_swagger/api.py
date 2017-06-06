# -*- coding: utf-8 -*-
"""
Module for automatically serving /api-docs* via Pyramid.
"""
import copy
import os.path

import simplejson
import yaml
from bravado_core.spec import strip_xscope
from six.moves.urllib.parse import urlparse
from six.moves.urllib.parse import urlunparse

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


def _low_level_translate(url, is_marshaling=True):
    """
    Translate the URL string representation into a new string which could be
    used as JSON keys.
    Example: if the url is "#/definitions/data_type" it could not be directly
    injected into the JSON as a key since many parser could comply with it.
    To workaround this limitation we can re-write the url representation in a
    way that the parsers will accept it, for example "#/definitions/data_type"
    could become "|..definitions..data_type"

    :param url: string representation of an url (the expected format is
        '[{scheme}://][{host}]{path}[#{fragment}]')
    :type url: str
    :param is_marshaling: flag representing the marshaling (to JSON) or the
        un-marshaling (from JSON) operation
    :type is_marshaling: bool
    :return: a string representation of the URL which could be used into the
        JSON keys
    """
    # replacement of the scheme (valid only in un-marshaling phase)
    scheme_replacements = [  # defined as tuples (un-marshaled, marshaled)
        ('file://', 'file.'),
        ('http://', 'http.'),
        ('https://', 'https.'),
    ]
    # replacement over the whole string
    replacement_patterns = [  # defined as tuples (un-marshaled, marshaled)
        ('/', '..'),
        ('#', '|'),
    ]

    # repl_idx allow to prevent if statements over the code execution
    # instead of doing:
    #       if is_marshaling:
    #           x = x.replace(replacement[0], replacement[1])
    #       else:
    #           x = x.replace(replacement[1], replacement[0])
    # we can achieve the same doing
    #       x = x.replace(replacement[repl_idx], replacement[1-repl_idx])
    repl_idx = 0 if is_marshaling else 1
    replaced_scheme = ''
    for replacement in scheme_replacements:
        if url.startswith(replacement[repl_idx]):
            replaced_scheme = replacement[1 - repl_idx]
            url = url[len(replacement[repl_idx]):]
            break
    for replacement in replacement_patterns:
        url = url.replace(replacement[repl_idx], replacement[1 - repl_idx])
    return replaced_scheme + url


def _get_absolute_link(spec, resource_path_fragment, current_path=''):
    """
    Generate an absolute link starting form the relative path and the
    current_path information.

    :param spec: Swagger Spec
    :type spec: bravado_core.spec.Spec
    :param resource_path_fragment: path and fragment of the resource
        (the expected format is '{path}#{fragment}')
    :type resource_path_fragment: str
    :param current_path: local or remote base path used for the absolute URL
        generation. It represent the path of the resource in which is defined
        the target/reference.
    :type current_path: str
    :return: URL containing the absolute path associated to the relative_path
    """
    spec_url = urlparse(spec.origin_url)
    spec_file = os.path.abspath(spec_url.path)
    spec_dir = os.path.dirname(spec_file)

    current_path_url = urlparse(current_path)

    target_url = urlparse(resource_path_fragment)
    if len(target_url.scheme) > 0:
        target_scheme = target_url.scheme
    elif len(current_path_url.scheme) > 0:
        target_scheme = current_path_url.scheme
    else:
        target_scheme = 'file'

    if target_scheme == 'file':  # targeting a local file
        # if not absolute path, make it absolute
        if not target_url.path.startswith('/'):
            # if path is empty, then is targeting to the current file
            filename = target_url.path if len(target_url.path) > 0 \
                else os.path.basename(current_path_url.path)
            target_url = urlparse('{path}#{fragment}'.format(
                path=os.path.join(
                    spec_dir,
                    os.path.dirname(current_path_url.path),
                    filename,
                ),
                fragment=target_url.fragment,
            ))
        return target_url

    elif target_scheme in ['http', 'https']:
        remote_path = os.path.abspath(os.path.join(
            current_path_url.path if len(current_path_url.path) > 0 else '/',
            target_url.path
        ))
        return urlparse('{scheme}://{hostname}{path}#{fragment}'.format(
            scheme=target_scheme,
            hostname=target_url.hostname,
            path=remote_path,
            fragment=target_url.fragment,
        ))
    else:
        return urlparse(resource_path_fragment)


def _get_target_url(spec, target, current_path=''):
    """
    Generate a well formatted URL for the required target.
    NOTE: The method assumes that the base swagger definition file
    (swagger.{json,yaml}) is a server local file.

    The URL ({schema}://{host}{path}#{fragment}) will be:
        - fully defined for a remote resources
          The URL associated to "$ref": "http://link/path.json#/definitions/dt)
          is "http://link/path.json#/definitions/dt"
        - not fully defined for local resources. The schema and host components
          of the URL will be empty and the path will contain only the relative
          path respect to the base swagger file (swagger.{json,yaml})
    NOTE: We are not fully referencing the local resources in order to limit as
    much as possible the amount of information that are made public (ie. the
    complete server paths containing the swagger files). The limitation, of
    server related, information will make harder for an intruder to forge or
    modify the server specifications.

    :param spec: Swagger Spec
    :type spec: bravado_core.spec.Spec
    :param target: URL of the target that has to be formatted
    :type target: str
    :param current_path: local or remote base path used for the absolute URL
        generation. It represent the path of the resource in which is defined
        the target/reference.
    :type current_path: str
    :return: url associated to the target resource
    """
    if target == '':
        raise ValueError('Empty target')

    target_url = _get_absolute_link(spec, target, current_path)
    target_scheme = 'file' if target_url.scheme == '' else target_url.scheme

    if target_scheme == 'file':
        spec_dir = os.path.dirname(urlparse(spec.origin_url).path)
        # Hiding of the internal server paths information.
        # A path relative to the swagger.{json,yaml} is returned
        target_url = urlparse('{path}#{fragment}'.format(
            path=os.path.relpath(target_url.path, spec_dir),
            fragment=target_url.fragment,
        ))

    if target_scheme in ['file', 'http', 'https']:
        return target_url
    else:  # Handle the case of an unknown target scheme
        raise ValueError(
            'Invalid target: {target}'.format(target=target)
        )


def _ensure_sane_key(fragment, mar_target):
    '''
    This function patches a nasty bug with the
    which was corrupting out keys

    explanation:
        sometimes the fragment becomes:
        '/definitions/:........swagger|..definitions..A'
        and which makes the marshaled_target:
        ':........swagger|..definitions..:........swagger|..definitions..A'
        this is bad, it only comes about in a very specific case
        this function esentially checks for that.
    In the above example we want to return: ':........swagger|..definitions..A'

    see tests/sample_specs/nested_defns/swagger.yaml
    for an example spec that causes this issue.

    '''
    simple_fragment = fragment.split('/')[-1]
    path_to_key = simple_fragment.split('..')
    path = path_to_key[:-1]
    key = path_to_key[-1]
    bad_path = '..'.join(path + path + [key])
    if bad_path == mar_target:
        return '..'.join(path + [key])
    return mar_target


def _marshal_target(target_url):
    target_scheme = target_url.scheme
    target_fragment = target_url.fragment
    if len(target_url.path) > 0 and \
            target_scheme in ['', 'file', 'http', 'https']:
        marshaled_target = _low_level_translate(
            '{scheme}://{host}{path}#{fragment}'.format(
                scheme=target_url.scheme,
                host=target_url.hostname if target_url.hostname else '',
                path=target_url.path,
                fragment=target_fragment,
            ))
        return _ensure_sane_key(target_fragment, marshaled_target)
    else:
        raise ValueError(
            'Invalid target: {target}'.format(target=urlunparse(target_url))
        )


def _unmarshal_target(marshaled_target):
    if any(marshaled_target.startswith(x) for x in
           ('file.', 'http.', 'https.')):
        result = _low_level_translate(marshaled_target, is_marshaling=False)
        # Remove the file:// scheme to allow the use of relative paths
        if not result.startswith('file:///'):
            result = result.replace('file://', '')
        return result
    else:
        raise ValueError(
            'Invalid marshaled object: {target}'.format(
                target=marshaled_target
            )
        )


def is_a_swagger_definition(json_path):
    """
    The method checks if json_path could have references to Swagger definitions
    (http://swagger.io/specification/#definitionsObject).

    :param json_path: json path to check
    :type json_path: list
    :return: true if json_path could have references toward Swagger definition
    objects, false otherwise
    :type: bool
    """
    # According to the Swagger specifications only a subset of paths could
    # target a Swagger definition object.
    # The paths that could led to a Swagger definition object are:
    # '/definitions/.*', '.*/schema',  '.*/items' and '.*/allOf'
    return json_path == ['definitions'] or \
        json_path[-1] in ['schema', 'items', 'allOf']


def resolve_ref(spec, url, json_path, file_path, defs_dict):
    with spec.resolver.resolving(url) as resolved_spec_dict:
        spec_dict = copy.deepcopy(resolved_spec_dict)
        return resolve_refs(spec, spec_dict, json_path, file_path, defs_dict)


def make_resolved_ref(marshaled_target):
    return {'$ref': '#/definitions/{target}'.format(
        target=marshaled_target,
    )}


def resolve_refs(spec, val, json_path, file_path, defs_dict):
    if isinstance(val, dict):
        new_dict = {}
        for key, subval in val.items():
            if key == '$ref':
                if is_a_swagger_definition(json_path):
                    target_url = _get_target_url(spec, subval, file_path)
                    marshaled_target = _marshal_target(target_url)
                    if marshaled_target not in defs_dict:
                        defs_dict[marshaled_target] = None  # placeholder
                        # The placeholder is present to interrupt the recursion
                        # during the resolve_ref of a recursive data model
                        defs_dict[marshaled_target] = resolve_ref(
                            spec, subval, json_path, file_path, defs_dict
                        )
                    return make_resolved_ref(marshaled_target)
                # assume $ref is the only key in the dict
                return resolve_ref(
                    spec, subval, json_path, file_path, defs_dict
                )
            else:
                new_dict[key] = resolve_refs(
                    spec, subval, json_path + [key], file_path, defs_dict
                )
        return new_dict

    if isinstance(val, list):
        for index, subval in enumerate(val):
            val[index] = resolve_refs(
                spec, subval, json_path + [index], file_path, defs_dict
            )
    return val


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
            spec_file_name = os.path.basename(urlparse(spec.origin_url).path)
            defs_dict = {}
            resolved_dict = resolve_refs(spec, spec_copy, ['/'],
                                         spec_file_name, defs_dict)
            if len(defs_dict) > 0:
                resolved_dict.update({'definitions': defs_dict})
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
        _, ext = os.path.splitext(request.path)
        ext = ext.lstrip('.')

        base_path = config.registry.settings\
            .get('pyramid_swagger.base_path_api_docs', '').rstrip('/')

        key_path = request.path_info[len(base_path):]

        actual_fname = file_map[key_path]

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
