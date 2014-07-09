# -*- coding: utf-8 -*-
"""Unit tests for tweens.py"""
import mock
import pytest
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.response import Response

from pyramid_swagger.tween import prepare_body
from pyramid_swagger.tween import validation_tween_factory


def test_response_charset_missing_raises_5xx():
    with pytest.raises(HTTPInternalServerError):
        prepare_body(
            Response(content_type='foo')
        )


def test_unconfigured_schema_dir_raises_error():
    """If we send a settings dict without schema_dir, fail fast."""
    with pytest.raises(ValueError):
        validation_tween_factory(
            mock.ANY,
            mock.Mock(settings={})
        )
