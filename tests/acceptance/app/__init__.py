# -*- coding: utf-8 -*-
import webob
from pyramid.config import Configurator
from pyramid.view import view_config


@view_config(route_name='throw_400', renderer='json')
def throw_error(request):
    request.response.status = webob.exc.HTTPBadRequest.code
    return dict(error=dict(details='Throwing error!'))


@view_config(route_name='standard', renderer='json')
def standard(request, path_arg):
    return {
        'raw_response': 'foo',
        'logging_info': {},
    }


@view_config(route_name='sample_nonstring', renderer='json')
@view_config(route_name='get_with_non_string_query_args', renderer='json')
@view_config(route_name='post_with_primitive_body', renderer='json')
@view_config(route_name='sample_header', renderer='json')
@view_config(route_name='sample_post', renderer='json')
@view_config(route_name='post_with_form_params', renderer='json')
@view_config(route_name='post_with_file_upload', renderer='json')
def sample(request):
    if not request.registry.settings.get('skip_swagger_data_assert'):
        assert request.swagger_data
    return {}


def main(global_config, **settings):
    """ Very basic pyramid app """
    config = Configurator(settings=settings)

    config.include('pyramid_swagger')

    config.add_route(
        'sample_nonstring',
        '/sample/nonstring/{int_arg}/{float_arg}/{boolean_arg}',
    )
    config.add_route('standard', '/sample/{path_arg}/resource')
    config.add_route(
        'get_with_non_string_query_args',
        '/get_with_non_string_query_args',
    )
    config.add_route('post_with_primitive_body', '/post_with_primitive_body')
    config.add_route('post_with_form_params', '/post_with_form_params')
    config.add_route('post_with_file_upload', '/post_with_file_upload')
    config.add_route('sample_post', '/sample')
    config.include(include_samples, route_prefix='/sample')
    config.add_route('throw_400', '/throw_400')

    config.scan()
    return config.make_wsgi_app()


def include_samples(config):
    config.add_route('sample_header', '/header')
