# -*- coding: utf-8 -*-
import os

import pytest


@pytest.fixture
def test_dir():
    return os.path.abspath(os.path.dirname(__file__))
