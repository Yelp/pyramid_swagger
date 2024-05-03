# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime
from contextlib import contextmanager

import pytest
import simplejson
from pyramid.httpexceptions import exception_response
from webtest.utils import NoDefault

from pyramid_swagger import exceptions


def build_test_app(swagger_versions, **overrides):
    """Fixture for setting up a test test_app with particular settings."""
    from tests.acceptance.app import main
    from webtest import TestApp as App
    settings = dict({
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_response_validation': False,
        'pyramid_swagger.enable_swagger_spec_validation': False,
        'pyramid_swagger.swagger_versions': swagger_versions},
        **overrides
    )

    return App(main({}, **settings))


# Parameterize pyramid_swagger.swagger_versions
# Swagger 1.2 tests are broken. Swagger 1.2 is deprecated and thus we have no plans to fix these tests,
# so they have been removed.
@pytest.fixture(
    params=[['2.0'], ],
    ids=['2.0', ],
)
def test_app(request):
    """Fixture for setting up a test test_app with particular settings."""
    return build_test_app(
        swagger_versions=request.param,
    )


@contextmanager
def validation_context(request, response=None):
    try:
        yield
    except (
        exceptions.RequestValidationError,
        exceptions.ResponseValidationError,
        exceptions.PathNotFoundError,
    ):
        raise exception_response(206)
    except Exception:
        raise exception_response(400)


validation_ctx_path = 'tests.acceptance.request_test.validation_context'


def test_echo_date_with_pyramid_swagger_renderer(test_app):
    input_object = {'date': datetime.date.today().isoformat()}

    response = test_app.post_json('/echo_date', input_object)

    # If the request is served via Swagger1.2
    assert response.status_code == 200
    assert response.json == input_object


def test_echo_date_with_json_renderer(test_app):
    today = datetime.date.today()
    input_object = {'date': today.isoformat()}

    exc = None
    response = None
    try:
        response = test_app.post_json('/echo_date_json_renderer', input_object)
    except TypeError as exception:
        exc = exception

    served_swagger_versions = test_app.app.registry.settings['pyramid_swagger.swagger_versions']

    if '2.0' in served_swagger_versions:
        # If the request is served via Swagger2.0, pyramid_swagger will perform types
        # conversions providing a datetime.date object in the pyramid view
        assert exc.args == ('{!r} is not JSON serializable'.format(today), )
    else:
        # If the request is served via Swagger1.2 there are no implicit type conversions performed by pyramid_swagger
        assert response.status_code == 200
        assert response.json == input_object


@pytest.mark.parametrize(
    'body, expected_length',
    [
        [NoDefault, 0],
        [{}, 2],
    ],
)
def test_post_endpoint_with_optional_body(test_app, body, expected_length):
    assert test_app.post_json('/post_endpoint_with_optional_body', body).json == expected_length


def test_200_with_form_params(test_app):
    assert test_app.post(
        '/post_with_form_params',
        {'form_param': 42},
    ).status_code == 200


def test_200_with_file_upload(test_app):
    assert test_app.post(
        '/post_with_file_upload',
        upload_files=[('photo_file', 'photo.jpg', b'<binary data goes here>')],
    ).status_code == 200


def test_400_with_form_params_wrong_type(test_app):
    assert test_app.post(
        '/post_with_form_params',
        {'form_param': "not a number"},
        expect_errors=True,
    ).status_code == 400


def test_400_if_json_body_for_form_parms(test_app):
    assert test_app.post_json(
        '/post_with_form_params',
        {'form_param': 42},
        expect_errors=True,
    ).status_code == 400


def test_400_if_required_query_args_absent(test_app):
    assert test_app.get(
        '/sample/path_arg1/resource',
        expect_errors=True,
    ).status_code == 400


def test_200_if_optional_query_args_absent(test_app):
    assert test_app.get(
        '/sample/path_arg1/resource',
        params={'required_arg': 'test'},  # no `optional_arg` arg
    ).status_code == 200


def test_200_if_request_arg_is_wrong_type(test_app):
    assert test_app.get(
        '/sample/path_arg1/resource',
        params={'required_arg': 1.0},
    ).status_code == 200


def test_200_if_request_arg_types_are_not_strings(test_app):
    assert test_app.get(
        '/get_with_non_string_query_args',
        params={
            'int_arg': '5',
            'float_arg': '3.14',
            'boolean_arg': 'true',
        },
    ).status_code == 200


def test_404_if_path_not_in_swagger(test_app):
    assert test_app.get(
        '/undefined/path',
        expect_errors=True,
    ).status_code == 404


def test_200_skip_validation_with_excluded_path():
    app = build_test_app(
        swagger_versions=['2.0'],
        **{'pyramid_swagger.exclude_paths': [r'^/undefined/path']}
    )
    assert app.get('/undefined/path').status_code == 200


def test_400_if_request_arg_is_wrong_type_but_not_castable(test_app):
    assert test_app.get(
        '/get_with_non_string_query_args',
        params={'float_arg': 'foobar'},
        expect_errors=True,
    ).status_code == 400


def test_400_if_path_arg_not_valid_enum(test_app):
    assert test_app.get(
        '/sample/invalid_arg/resource',
        params={'required_arg': 'test'},
        expect_errors=True,
    ).status_code == 400


def test_200_if_path_arg_is_wrong_type_but_castable(test_app):
    assert test_app.get(
        '/sample/nonstring/3/1.4/false',
    ).status_code == 200


def test_400_if_required_body_is_missing(test_app):
    assert test_app.post_json(
        '/sample',
        {},
        expect_errors=True,
    ).status_code == 400


def test_200_on_json_body_without_contenttype_header(test_app):
    """See https://github.com/striglia/pyramid_swagger/issues/49."""
    # We use .post to avoid sending a Content Type of application/json.
    assert test_app.post(
        '/sample?optional_string=bar',
        simplejson.dumps({'foo': 'test'}),
        {'Content-Type': ''},
    ).status_code == 200


def test_400_if_body_has_missing_required_arg(test_app):
    assert test_app.post_json(
        '/sample',
        {'bar': 'test'},
        expect_errors=True,
    ).status_code == 400


def test_200_if_body_has_missing_optional_arg(test_app):
    assert test_app.post_json(
        '/sample',
        {'foo': 'test'},
    ).status_code == 200


def test_200_if_required_body_is_model(test_app):
    assert test_app.post_json(
        '/sample',
        {'foo': 'test', 'bar': 'test'},
    ).status_code == 200


def test_200_if_required_body_is_primitives(test_app):
    assert test_app.post_json(
        '/post_with_primitive_body',
        ['foo', 'bar'],
    ).status_code == 200


def test_400_if_extra_body_args(test_app):
    assert test_app.post_json(
        '/sample',
        {'foo': 'test', 'bar': 'test', 'made_up_argument': 1},
        expect_errors=True,
    ).status_code == 400


def test_400_if_extra_query_args(test_app):
    assert test_app.get(
        '/sample/path_arg1/resource?made_up_argument=1',
        expect_errors=True,
    ).status_code == 400


def test_400_if_missing_required_header(test_app):
    assert test_app.get(
        '/sample/header',
        expect_errors=True,
    ).status_code == 400


def test_200_with_required_header(test_app):
    response = test_app.get(
        '/sample/header',
        headers={'X-Force': 'True'},
        expect_errors=True,
    )
    assert response.status_code == 200


def test_200_skip_validation_when_disabled():
    # calling endpoint with required args missing
    overrides = {
        'pyramid_swagger.enable_request_validation': False,
        'skip_swagger_data_assert': True,
    }
    app = build_test_app(
        swagger_versions=['2.0'],
        **overrides
    )
    response = app.get('/get_with_non_string_query_args', params={})
    assert response.status_code == 200


def test_path_validation_context():
    app = build_test_app(
        swagger_versions=['2.0'],
        **{'pyramid_swagger.validation_context_path': validation_ctx_path}
    )
    assert app.get('/does_not_exist').status_code == 206


def test_request_validation_context():
    app = build_test_app(
        swagger_versions=['2.0'],
        **{'pyramid_swagger.validation_context_path': validation_ctx_path})
    response = app.get('/get_with_non_string_query_args', params={})
    assert response.status_code == 206


def test_request_to_authenticated_endpoint_without_authentication():
    app = build_test_app(swagger_versions=['2.0'])
    response = app.get(
        '/sample/authentication',
        expect_errors=True,
    )
    assert response.status_code == 401


def test_request_to_endpoint_with_no_response_schema():
    app = build_test_app(swagger_versions=['2.0'])
    response = app.get('/sample/no_response_schema')
    assert response.status_code == 200
