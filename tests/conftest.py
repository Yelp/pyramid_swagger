# -*- coding: utf-8 -*-
import os

import pytest


@pytest.yield_fixture(autouse=True)
def _set_current_directory_to_git_repo_root():
    """
    During tests execution make sure that current working directory
    is set accordingly to git repository root.
    It will allow to run tests with relative file import with the
    same reference path.
    """
    repo_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    curdir = os.getcwd()
    try:
        os.chdir(repo_root_path)
        yield
    finally:
        os.chdir(curdir)
