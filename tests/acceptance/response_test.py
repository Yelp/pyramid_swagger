from .request_test import test_app


def test_200_for_normal_response_validation():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.enable_response_validation': True,
    }
    test_app(settings).post_json(
        '/sample',
        {'foo': 'test', 'bar': 'test'},
        status=200
    )


def test_200_skip_validation_with_wrong_response():
    settings = {
        'pyramid_swagger.schema_directory': 'tests/sample_schemas/good_app/',
        'pyramid_swagger.skip_validation': '/(sample)\\b',
    }
    test_app(settings).get(
        '/sample/path_arg1/resource',
        params={'required_arg': 'test'},
        status=200
    )
