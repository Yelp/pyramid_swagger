from .request_test import test_app


def test_200_for_normal_response_validation():
    settings = {
        'pyramid_swagger.schema_path': 'tests/acceptance/app/swagger.json',
        'pyramid_swagger.enable_response_validation': True,
    }
    res = test_app(settings).post_json(
        '/sample_post',
        {'foo': 'test', 'bar': 'test'},
    )
    assert res.status_code == 200


def test_200_skip_validation_with_wrong_response():
    settings = {
        'pyramid_swagger.schema_path': 'tests/acceptance/app/swagger.json',
        'pyramid_swagger.skip_validation': '/(sample)\\b',
    }
    res = test_app(settings).get(
        '/sample/path_arg1/resource',
        params={'required_arg': 'test'},
    )
    assert res.status_code == 200
