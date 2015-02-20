import mock

import pyramid_swagger


@mock.patch('pyramid_swagger.register_api_doc_endpoints')
def test_disable_api_doc_views(mock_register):
    settings = {
        'pyramid_swagger.enable_api_doc_views': False,
    }
    mock_config = mock.Mock(registry=mock.Mock(settings=settings))
    pyramid_swagger.includeme(mock_config)
    assert not mock_register.called
