# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime
import json

import pytest
from bravado_core.exception import MatchingResponseNotFound
from bravado_core.exception import SwaggerMappingError
from bravado_core.operation import Operation
from bravado_core.spec import Spec
from mock import mock
from pyramid.testing import DummyRequest

from pyramid_swagger import PyramidSwaggerRendererFactory
from pyramid_swagger import renderer


class TestPyramidSwaggerRendererFactoryUnitTest(object):

    @pytest.yield_fixture
    def mock_marshal_schema_object(self):
        with mock.patch('pyramid_swagger.renderer.marshal_schema_object') as _mock:
            yield _mock

    @pytest.yield_fixture
    def mock_get_response_spec(self):
        with mock.patch('pyramid_swagger.renderer.get_response_spec') as _mock:
            yield _mock

    def setup_method(self, method):
        self.info = mock.Mock(name='info')
        self.value_to_render = mock.Mock(name='value_to_render')
        self.mock_spec = mock.Mock(spec=Spec)
        self.mock_request = DummyRequest(
            swagger_data=mock.Mock(spec=dict),
            operation=mock.Mock(spec=Operation),
        )
        self.mock_request.registry.settings = {'pyramid_swagger.schema20': self.mock_spec}
        self.mock_system = {'request': self.mock_request}
        self.external_renderer_factory = mock.Mock(name='external_renderer_factory')

    def test_successiful_rendering_flow(self, mock_get_response_spec, mock_marshal_schema_object):
        renderer_factory = PyramidSwaggerRendererFactory(renderer_factory=self.external_renderer_factory)

        renderer = renderer_factory(info=self.info)
        rendered_value = renderer(self.value_to_render, self.mock_system)

        self.external_renderer_factory.assert_called_once_with(self.info)
        mock_get_response_spec.assert_called_once_with(
            op=self.mock_request.operation,
            status_code=self.mock_request.response.status_code,
        )
        mock_marshal_schema_object.assert_called_once_with(
            schema_object_spec=mock_get_response_spec.return_value.__getitem__.return_value,
            swagger_spec=self.mock_spec,
            value=self.value_to_render,
        )
        self.external_renderer_factory.return_value.assert_called_once_with(
            mock_marshal_schema_object.return_value,
            self.mock_system,
        )
        assert rendered_value == self.external_renderer_factory.return_value.return_value

    def test_rendering_operation_not_found(self, mock_get_response_spec, mock_marshal_schema_object):
        renderer_factory = PyramidSwaggerRendererFactory(renderer_factory=self.external_renderer_factory)
        self.mock_request.operation = None

        renderer = renderer_factory(info=self.info)
        rendered_value = renderer(self.value_to_render, self.mock_system)

        self.external_renderer_factory.assert_called_once_with(self.info)
        assert not mock_get_response_spec.called
        assert not mock_marshal_schema_object.called
        self.external_renderer_factory.return_value.assert_called_once_with(
            self.value_to_render,
            self.mock_system,
        )
        assert rendered_value == self.external_renderer_factory.return_value.return_value

    def test_rendering_response_spec_not_found(self, mock_get_response_spec, mock_marshal_schema_object):
        renderer_factory = PyramidSwaggerRendererFactory(renderer_factory=self.external_renderer_factory)
        mock_get_response_spec.side_effect = MatchingResponseNotFound

        renderer = renderer_factory(info=self.info)
        rendered_value = renderer(self.value_to_render, self.mock_system)

        self.external_renderer_factory.assert_called_once_with(self.info)
        mock_get_response_spec.assert_called_once_with(
            op=self.mock_request.operation,
            status_code=self.mock_request.response.status_code,
        )
        assert not mock_marshal_schema_object.called
        self.external_renderer_factory.return_value.assert_called_once_with(
            self.value_to_render,
            self.mock_system,
        )
        assert rendered_value == self.external_renderer_factory.return_value.return_value

    def test_rendering_response_without_schema(self, mock_get_response_spec, mock_marshal_schema_object):
        renderer_factory = PyramidSwaggerRendererFactory(renderer_factory=self.external_renderer_factory)
        mock_get_response_spec.return_value = {'200': {'description': ''}}

        renderer = renderer_factory(info=self.info)
        rendered_value = renderer(self.value_to_render, self.mock_system)

        self.external_renderer_factory.assert_called_once_with(self.info)
        mock_get_response_spec.assert_called_once_with(
            op=self.mock_request.operation,
            status_code=self.mock_request.response.status_code,
        )
        assert not mock_marshal_schema_object.called
        self.external_renderer_factory.return_value.assert_called_once_with(
            self.value_to_render,
            self.mock_system,
        )
        assert rendered_value == self.external_renderer_factory.return_value.return_value

    def test_rendering_error_during_marshaling(self, mock_get_response_spec, mock_marshal_schema_object):
        renderer_factory = PyramidSwaggerRendererFactory(renderer_factory=self.external_renderer_factory)
        mock_marshal_schema_object.side_effect = SwaggerMappingError

        renderer = renderer_factory(info=self.info)
        rendered_value = renderer(self.value_to_render, self.mock_system)

        self.external_renderer_factory.assert_called_once_with(self.info)
        mock_get_response_spec.assert_called_once_with(
            op=self.mock_request.operation,
            status_code=self.mock_request.response.status_code,
        )
        mock_marshal_schema_object.assert_called_once_with(
            schema_object_spec=mock_get_response_spec.return_value.__getitem__.return_value,
            swagger_spec=self.mock_spec,
            value=self.value_to_render,
        )
        self.external_renderer_factory.return_value.assert_called_once_with(
            self.value_to_render,
            self.mock_system,
        )
        assert rendered_value == self.external_renderer_factory.return_value.return_value


class TestPyramidSwaggerRendererFactoryIntegrationTest(object):
    swagger_spec_dict = {
        'swagger': '2.0',
        'info': {
            'title': 'A title',
            'version': '0.0.0',
        },
        'paths': {
            '/endpoint': {
                'get': {
                    'responses': {
                        '200': {
                            'description': 'HTTP/200 OK',
                            'schema': {
                                'properties': {
                                    'date': {
                                        'type': 'string',
                                        'format': 'date',
                                    }
                                },
                                'type': 'object',
                            },
                        },
                    },
                },
            },
        },
    }

    @pytest.yield_fixture(scope='session')
    def swagger_spec(self):
        spec = Spec.from_dict(self.swagger_spec_dict)
        yield spec

    @pytest.yield_fixture
    def mock_request(self, swagger_spec):
        mock_request = DummyRequest(
            swagger_data={},
            operation=swagger_spec.resources['endpoint'].get_endpoint,
        )
        mock_request.registry.settings = {'pyramid_swagger.schema20': swagger_spec}
        yield mock_request

    @pytest.yield_fixture
    def spy_marshal_schema_object(self):
        with mock.patch.object(renderer, 'marshal_schema_object', wraps=renderer.marshal_schema_object) as _mock:
            yield _mock

    @pytest.yield_fixture
    def spy_get_response_spec(self):
        with mock.patch.object(renderer, 'get_response_spec', wraps=renderer.get_response_spec) as _mock:
            yield _mock

    def setup_method(self, method):
        self.info = mock.Mock(name='info')
        self.renderer_factory = PyramidSwaggerRendererFactory()

    @pytest.mark.parametrize(
        'view_response, expected_rendered_value',
        [
            [None, 'null'],
            [{}, '{}'],
            [{'new_property': 'any value'}, '{"new_property": "any value"}'],
            [{'date': datetime.date.today()}, '{"date": "' + datetime.date.today().isoformat() + '"}'],
        ],
    )
    def test_no_errors(
        self, spy_get_response_spec, spy_marshal_schema_object,
        swagger_spec, mock_request, view_response, expected_rendered_value,
    ):
        system = {'request': mock_request}
        renderer = self.renderer_factory(info=self.info)
        rendered_value = renderer(view_response, system)

        spy_get_response_spec.assert_called_once_with(
            op=mock_request.operation,
            status_code=mock_request.response.status_code,
        )
        spy_marshal_schema_object.assert_called_once_with(
            schema_object_spec=self.swagger_spec_dict['paths']['/endpoint']['get']['responses']['200']['schema'],
            swagger_spec=swagger_spec,
            value=view_response,
        )

        assert rendered_value == expected_rendered_value

    @pytest.mark.parametrize(
        'view_response, expect_exernal_renderer_exception',
        [
            [None, False],
            [{}, False],
            [{'new_property': 'any value'}, False],
            [{'date': datetime.date.today()}, True],
        ],
    )
    def test_response_spec_not_found(
        self, spy_get_response_spec, spy_marshal_schema_object,
        mock_request, view_response, expect_exernal_renderer_exception,
    ):
        mock_request.response.status_code = 400
        system = {'request': mock_request}
        renderer = self.renderer_factory(info=self.info)

        rendered_value = None
        expected_rendered_value = None
        if expect_exernal_renderer_exception:
            with pytest.raises(Exception):
                # Expect exception because datetime.date object cannot be serialized by JSON pyramid renderer
                rendered_value = renderer(view_response, system)
        else:
            rendered_value = renderer(view_response, system)
            expected_rendered_value = json.dumps(view_response)

        spy_get_response_spec.assert_called_once_with(
            op=mock_request.operation,
            status_code=mock_request.response.status_code,
        )
        assert not spy_marshal_schema_object.called
        assert rendered_value == expected_rendered_value

    def test_marshaling_raise_exception(
        self, spy_get_response_spec, spy_marshal_schema_object, swagger_spec, mock_request,
    ):
        system = {'request': mock_request}
        value_to_renderer = {'date': datetime.date.today().isoformat()}

        renderer = self.renderer_factory(info=self.info)
        rendered_value = renderer(value_to_renderer, system)

        spy_get_response_spec.assert_called_once_with(
            op=mock_request.operation,
            status_code=mock_request.response.status_code,
        )
        spy_marshal_schema_object.assert_called_once_with(
            schema_object_spec=self.swagger_spec_dict['paths']['/endpoint']['get']['responses']['200']['schema'],
            swagger_spec=swagger_spec,
            value=value_to_renderer,
        )
        assert rendered_value == json.dumps(value_to_renderer)
