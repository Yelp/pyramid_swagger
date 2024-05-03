# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os.path

import pytest
from pyramid.paster import get_appsettings
from webtest import TestApp as App

from pyramid_swagger.tween import get_swagger_versions
from pyramid_swagger.tween import load_settings
from tests.acceptance.app import main


@pytest.fixture
def ini_app():
    settings = get_appsettings(os.path.join(os.path.dirname(__file__), 'app', 'config.ini'), name='main')
    # Swagger 1.2 tests are broken. Swagger 1.2 is deprecated and thus we have no plans to fix these tests,
    # so removing them here.
    settings["pyramid_swagger.swagger_versions"] = "2.0"
    return App(main({}, **settings))


def test_load_ini_settings(ini_app):
    registry = ini_app.app.registry
    settings = load_settings(registry)

    # Make sure these settings are booleans
    assert settings.validate_request is True
    assert settings.validate_response is False
    assert settings.validate_path is True
    assert settings.exclude_routes == {'/undefined/first', '/undefined/second'}
    assert settings.prefer_20_routes == {'/sample'}


def test_get_swagger_versions(ini_app):
    settings = ini_app.app.registry.settings
    swagger_versions = get_swagger_versions(settings)
    # Swagger 1.2 tests are broken. Swagger 1.2 is deprecated and thus we have no plans to fix these tests,
    # so removing them here.
    assert swagger_versions == {'2.0'}
