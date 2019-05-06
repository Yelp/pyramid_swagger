# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime

import six
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


@view_config(route_name='echo_date_json_renderer', request_method='POST', renderer='json')
@view_config(route_name='echo_date', request_method='POST', renderer='pyramid_swagger')
def date_view(request):

    if '2.0' in request.registry.settings['pyramid_swagger.swagger_versions']:
        # Swagger 2.0 endpoint handling
        assert isinstance(request.swagger_data['body']['date'], datetime.date)
    else:
        assert isinstance(request.swagger_data['body']['date'], six.string_types)

    return request.swagger_data['body']


@view_config(route_name='post_endpoint_with_optional_body', request_method='POST', renderer='pyramid_swagger')
def post_endpoint_with_optional_body(request):
    return request.content_length


@view_config(route_name='swagger_undefined', renderer='json')
def swagger_undefined(request):
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
    config.add_route('swagger_undefined', '/undefined/path')

    config.add_route('echo_date', '/echo_date')
    config.add_route('echo_date_json_renderer', '/echo_date_json_renderer')
    config.add_route('post_endpoint_with_optional_body', '/post_endpoint_with_optional_body')

    config.scan()
    return config.make_wsgi_app()


def include_samples(config):
    config.add_route('sample_header', '/header')
