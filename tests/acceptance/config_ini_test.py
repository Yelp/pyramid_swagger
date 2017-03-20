# -*- coding: utf-8 -*-
import os.path

import pytest
from pyramid.paster import get_appsettings
from webtest import TestApp as App

from .app import main
from pyramid_swagger.tween import load_settings


@pytest.fixture
def ini_app():
    settings = get_appsettings(os.path.join(os.path.dirname(__file__), 'app', 'config.ini'), name='main')
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
