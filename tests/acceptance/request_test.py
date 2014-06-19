import pytest


@pytest.fixture
def test_app(settings=None):
    """Fixture for setting up a test test_app with particular settings."""
    from .app import main
    from webtest import TestApp
    settings = settings or dict({
        'pyramid_swagger.schema_path': 'tests/acceptance/app/swagger.json',
        'pyramid_swagger.enable_response_validation': False,
        'pyramid_swagger.enable_swagger_spec_validation': False,
    })
    return TestApp(main({}, **settings))


def test_400_if_required_query_args_absent(test_app):
    res = test_app.get(
        '/sample/path_arg1/resource',
        expect_errors=True,
    )
    assert res.status_code == 400


def test_200_if_optional_query_args_absent(test_app):
    res = test_app.get(
        '/sample/path_arg1/resource',
        params={'required_arg': 'test'},  # no `optional_arg` arg
        expect_errors=True,
    )
    assert res.status_code == 200


def test_200_if_request_arg_is_wrong_type(test_app):
    res = test_app.get(
        '/sample/path_arg1/resource',
        params={'required_arg': 1.0},
        expect_errors=True,
    )
    assert res.status_code == 200


def test_200_if_request_arg_types_are_not_strings(test_app):
    res = test_app.get(
        '/get_with_non_string_query_args',
        params={
            'int_arg': '5',
            'float_arg': '3.14',
            'boolean_arg': 'true',
        },
        expect_errors=True,
    )
    assert res.status_code == 200


def test_400_if_path_not_in_swagger(test_app):
    res = test_app.get(
        '/does_not_exist',
        expect_errors=True,
    )
    assert res.status_code == 400


def test_400_if_request_arg_is_wrong_type_but_not_castable(test_app):
    res = test_app.get(
        '/get_with_non_string_query_args',
        params={'float_arg': 'foobar'},
        expect_errors=True,
    )
    assert res.status_code == 400


@pytest.mark.xfail(reason='Issue #13')
def test_400_if_path_arg_is_wrong_type(test_app):
    res = test_app.get(
        '/sample/invalid_arg/resource',
        params={'required_arg': 'test'},
        expect_errors=True,
    )
    assert res.status_code == 400


@pytest.mark.xfail(reason='Issue #13')
def test_200_if_path_arg_is_wrong_type_but_castable(test_app):
    res = test_app.get(
        '/sample/nonstring/3/1.4/false',
        expect_errors=True,
    )
    assert res.status_code == 200


def test_400_if_required_body_is_missing(test_app):
    res = test_app.post_json(
        '/sample_post',
        {},
        expect_errors=True,
    )
    assert res.status_code == 400


def test_400_if_body_has_missing_required_arg(test_app):
    res = test_app.post_json(
        '/sample_post',
        {'bar': 'test'},
        expect_errors=True,
    )
    assert res.status_code == 400


def test_200_if_body_has_missing_optional_arg(test_app):
    res = test_app.post_json(
        '/sample_post',
        {'foo': 'test'},
        expect_errors=True,
    )
    assert res.status_code == 200


def test_200_if_required_body_is_model(test_app):
    res = test_app.post_json(
        '/sample_post',
        {'foo': 'test', 'bar': 'test'},
        expect_errors=True,
    )
    assert res.status_code == 200


def test_200_if_required_body_is_primitives(test_app):
    res = test_app.post_json(
        '/post_with_primitive_body',
        ['foo', 'bar'],
        expect_errors=True,
    )
    assert res.status_code == 200
