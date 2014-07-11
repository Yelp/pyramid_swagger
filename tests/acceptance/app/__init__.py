from pyramid.config import Configurator
from pyramid.view import view_config


@view_config(route_name='sample_nonstring', renderer='json')
def sample_nonstring(request):
    return {}


@view_config(route_name='standard', renderer='json')
def standard(request, path_arg):
    return {
        'raw_response': 'foo',
        'logging_info': {},
    }


@view_config(route_name='get_with_non_string_query_args', renderer='json')
def get_with_non_string_query_args(request):
    return {}


@view_config(route_name='post_with_primitive_body', renderer='json')
def post_with_primitive_body(request):
    return {}


@view_config(route_name='sample_post', renderer='json')
def sample_post(request):
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
    config.add_route('sample_post', '/sample')

    config.scan()
    return config.make_wsgi_app()
