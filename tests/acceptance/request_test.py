# -*- coding: utf-8 -*-
from contextlib import contextmanager

import pytest
import simplejson
from _pytest.fixtures import FixtureRequest
from mock import Mock
from pyramid.httpexceptions import exception_response


# Parameterize pyramid_swagger.swagger_versions
@pytest.fixture(params=[['1.2'], ['2.0'], ['1.2', '2.0']])
def test_app(request, **overrides):
    """Fixture for setting up a test test_app with particular settings."""
    from .app import main
    from webtest import TestApp as App
    settings = dict({
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_request_validation': True,
        'pyramid_swagger.enable_response_validation': False,
        'pyramid_swagger.enable_swagger_spec_validation': False,
        'pyramid_swagger.swagger_versions': request.param},
        **overrides
    )
    return App(main({}, **settings))


@pytest.fixture(params=[['1.2'], ['2.0'], ['1.2', '2.0']])
def test_app_disabled_path_validation(request, **overrides):
    from copy import deepcopy
    new_overrides = deepcopy(overrides)
    new_overrides['pyramid_swagger.enable_path_validation'] = False
    return test_app(request, **new_overrides)


@contextmanager
def validation_context(request, response=None):
    try:
        yield
    except Exception:
        raise exception_response(206)


validation_ctx_path = 'tests.acceptance.request_test.validation_context'


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
        '/path_not_defined_by_any_swagger',
        expect_errors=True,
    ).status_code == 404


def test_200_if_path_not_in_swagger_and_path_validation_disabled(
        test_app_disabled_path_validation
):
    assert test_app_disabled_path_validation.get(
        '/path_not_defined_by_any_swagger',
    ).status_code == 200


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


def test_200_skip_validation_with_excluded_path():
    app = test_app(
        request=Mock(spec=FixtureRequest, param=['2.0']),
        **{'pyramid_swagger.exclude_paths': [r'^/sample/?']}
    )
    assert app.get('/sample/test_request/resource').status_code == 200


def test_200_skip_validation_when_disabled():
    # calling endpoint with required args missing
    overrides = {
        'pyramid_swagger.enable_request_validation': False,
        'skip_swagger_data_assert': True,
    }
    app = test_app(
        request=Mock(spec=FixtureRequest, param=['2.0']),
        **overrides
    )
    response = app.get('/get_with_non_string_query_args', params={})
    assert response.status_code == 200


def test_path_validation_context():
    app = test_app(
        request=Mock(spec=FixtureRequest, param=['2.0']),
        **{'pyramid_swagger.validation_context_path': validation_ctx_path}
    )
    assert app.get('/does_not_exist').status_code == 206


def test_request_validation_context():
    app = test_app(
        request=Mock(spec=FixtureRequest, param=['2.0']),
        **{'pyramid_swagger.validation_context_path': validation_ctx_path})
    response = app.get('/get_with_non_string_query_args', params={})
    assert response.status_code == 206
