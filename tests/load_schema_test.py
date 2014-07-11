from pyramid.testing import DummyRequest

from pyramid_swagger.api import build_api_declaration_view


def test_basepath_rewriting():
    resource_json = {'basePath': 'bar'}
    view = build_api_declaration_view(resource_json)
    request = DummyRequest(application_url='foo')
    result = view(request)
    assert result['basePath'] == request.application_url
    assert result['basePath'] != resource_json['basePath']
