# -*- coding: utf-8 -*-
"""
Module for automatically serving /api-docs* via Pyramid.
"""
import copy
import os.path
import simplejson
import yaml


from bravado_core.spec import strip_xscope
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


def _low_level_translate(path, is_marshaling=True):
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
        if path.startswith(replacement[repl_idx]):
            replaced_scheme = replacement[1 - repl_idx]
            path = path[len(replacement[repl_idx]):]
            break
    for replacement in replacement_patterns:
        path = path.replace(replacement[repl_idx], replacement[1 - repl_idx])
    return replaced_scheme + path


def _get_absolute_link(spec, relative_path, current_path=''):
    spec_url = urlparse(spec.origin_url)
    spec_file = os.path.abspath(spec_url.path)
    spec_dir = os.path.dirname(spec_file)

    current_path_url = urlparse(current_path)

    target_url = urlparse(relative_path)
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
        return urlparse(relative_path)


def _relpath(path, start):
    """Return a relative version of a path
    NOTE: Code duplicated from Python 2.7.9 implementation because the default
    implementation available on Python 2.6.9 is bugged.
    Some lines are removed due to the particular constraints added by the code
    """
    # if not path:
    #     raise ValueError("no path specified")

    start_list = [x for x in os.path.abspath(start).split(os.path.sep) if x]
    path_list = [x for x in os.path.abspath(path).split(os.path.sep) if x]

    # Work out how much of the filepath is shared by start and path.
    i = len(os.path.commonprefix([start_list, path_list]))

    rel_list = [os.path.pardir] * (len(start_list) - i) + path_list[i:]
    # if not rel_list:
    #     return os.path.curdir
    return os.path.join(*rel_list)


def _get_target(spec, target, current_path=''):
    # Note: we assume that swagger.json file is always a server-local file

    if target == '':
        raise ValueError('Empty target')

    target_url = _get_absolute_link(spec, target, current_path)
    target_scheme = 'file' if target_url.scheme == '' else target_url.scheme

    if target_scheme == 'file':
        spec_dir = os.path.dirname(urlparse(spec.origin_url).path)
        target_url = urlparse('{path}#{fragment}'.format(
            path=_relpath(target_url.path, spec_dir),
            fragment=target_url.fragment,
        ))

    if target_scheme in ['file', 'http', 'https']:
        return target_url
    else:
        raise ValueError(
            'Invalid target: {target}'.format(target=target)
        )


def _marshal_target(target_url):
    target_scheme = target_url.scheme
    if len(target_url.path) > 0 and \
            target_scheme in ['', 'file', 'http', 'https']:
        value = _low_level_translate(
            '{scheme}://{host}{path}#{fragment}'.format(
                scheme=target_url.scheme if len(target_scheme) > 0 else 'file',
                host=target_url.hostname if target_url.hostname else '',
                path=target_url.path,
                fragment=target_url.fragment,
            ))
        return value
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


def _is_model_definition(json_path, target_url):
    """
    According to the current json path and the targeted path if the
    reference resource could be injected into /definitions or have to be
    dereferenced in the current object

    :param json_path: path of the $ref into the JSON hierarchy
    :type json_path: list
    :param target_url: targeted path
    :type target_url: ParseResult
    :return: True if the target is a definition, False otherwise
    :rtype: bool
    """
    tag_for_model_def = (
        'definitions',
        'parameters',
        'items',
        'schema',
    )
    return target_url.fragment.startswith('/definitions/') or \
        any(tag in json_path for tag in tag_for_model_def)


def _fetch_reference(spec, target, file_path, defs_dict, json_path):
    """
    Fetch the target and update the defs_dict, if a definition is referenced.

    :param spec: bravado core swagger specification
    :type spec: bravado_core.spec.Spec
    :param target: target to be fetched
    :type target: str
    :param file_path: path containing the current base_json
    :type file_path: str
    :param defs_dict: known definitions
    :type defs_dict: dict
    :return: {'$ref': target conventional name} if targeting a definition,
             otherwise dereferenced object
    :rtype: dict
    """

    def _extract_reference(target):
        """
        Extract the target specification object

        :param target: target reference to be fetched
        :return: target specification dictionary
        :rtype: dict
        """
        with spec.resolver.resolving(target) as resolved_spec_dict:
            spec_dict = strip_xscope(resolved_spec_dict)  # remove x-scope info
            return spec_dict

    target_url = _get_target(spec, target, file_path)
    target = urlunparse(target_url)
    target_name = _marshal_target(target_url)
    if _is_model_definition(json_path, target_url):
        if target_name not in defs_dict:
            defs_dict[target_name] = None
            resolved = _resolve_references_rec(
                spec,
                # get the target specification
                _extract_reference(target),
                target_url.path,
                defs_dict,
                json_path,
            )
            defs_dict[target_name] = resolved
        return {"$ref": '#/definitions/{target}'.format(target=target_name)}
    else:
        return _resolve_references_rec(
            spec,
            # get the target specification
            _extract_reference(target),
            target_url.path,
            defs_dict,
        )


def _resolve_references_rec(spec, base_json, file_path, defs_dict,
                            json_path=[]):
    """
    Get self-contained swagger specifications of the base_json dictionary.
    The resulting swagger specifications are equivalent to the original specs,
    importing all the (eventual) specs available remotely or on different files

    :param spec: bravado core swagger specification
    :type spec: bravado_core.spec.Spec
    :param base_json: object to resolve
    :type base_json: dict
    :param file_path: path containing the current base_json
    :type file_path: str
    :param defs_dict: known definitions
    :type defs_dict: dict
    :return: swagger specification targeting definitions in defs_dict
    """

    if isinstance(base_json, dict):
        result_dict = {}
        for key, value in base_json.items():
            if key == '$ref':  # No assumption on only presence on the object
                result_dict.update(
                    _fetch_reference(spec, value, file_path,
                                     defs_dict, json_path)
                )
            else:
                result_dict[key] = _resolve_references_rec(
                    spec,
                    value,
                    file_path,
                    defs_dict,
                    [x for x in json_path] + [key]
                )
        return result_dict
    elif isinstance(base_json, list):
        result_list = []
        for index, item in enumerate(base_json):
            result_list.append(_resolve_references_rec(
                spec,
                item,
                file_path,
                defs_dict,
                json_path
            ))
        return result_list
    else:
        return base_json


def resolve_references(spec):
    """
    Get self-contained swagger specifications.
    The resulting swagger specifications are equivalent to the original specs,
    importing all the (eventual) specs available remotely or on different files

    The principal aim of this function is to generate an unique and consistent
    object which is logically equivalent to the original specs.

    It could be used to provides to the client the complete specs with a single
    call, avoiding possible issues in deployment environment in which multiple
    version of the service are available

    :param spec: bravado core swagger specification
    :type spec: bravado_core.spec.Spec
    :return: self-contained swagger specification
    :rtype: dict
    """

    defs_dict = {}
    spec_dict = strip_xscope(spec.client_spec_dict)

    # base file name of the swagger specs (no assumption on type and name)
    base_spec_file = os.path.basename(urlparse(spec.origin_url).path)

    if 'definitions' in spec_dict:
        for key, value in spec_dict['definitions'].items():
            target_name = _marshal_target(_get_target(
                spec,
                '#/definitions/{key}'.format(key=key),
                base_spec_file,
            ))
            defs_dict[target_name] = None
            resolved = _resolve_references_rec(spec, value, base_spec_file,
                                               defs_dict, ['definitions'])
            defs_dict[target_name] = resolved

        # strip out the definitions from the specs
        del spec_dict['definitions']

    # fetch the references the swagger model
    dereferenced_json = _resolve_references_rec(
        spec,
        spec_dict,
        base_spec_file,
        defs_dict,
        []
    )
    dereferenced_json['definitions'] = defs_dict

    return dereferenced_json


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
            resolved_dict = resolve_references(spec)
            settings['pyramid_swagger.schema20_resolved'] = resolved_dict
        return resolved_dict

    for schema_format in ['yaml', 'json']:
        route_name = 'pyramid_swagger.swagger20.api_docs.{0}' \
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
            route_name = 'pyramid_swagger.swagger20.api_docs.{0}.{1}' \
                .format(ref_fname.replace('/', '.'), schema_format)
            path = '/{0}.{1}'.format(ref_fname_parts[0], schema_format)
            file_map[path] = ref_fname
            yield PyramidEndpoint(
                path=path,
                route_name=route_name,
                view=view_for_swagger_schema,
                renderer=schema_format,
            )
