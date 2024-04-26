# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os

import yaml
from bravado_core.spec import Spec

from pyramid_swagger.api import get_path_if_relative


def test_ignore_absolute_paths():
    """
    we don't have the ability to automagically translate these external
    resources from yaml to json and vice versa, so ignore them altogether.
    """
    assert get_path_if_relative(
        'http://www.google.com/some/special/schema.json',
    ) is None

    assert get_path_if_relative(
        '//www.google.com/some/schema.yaml',
    ) is None

    assert get_path_if_relative(
        '/usr/lib/shared/schema.json',
    ) is None


def test_resolve_nested_refs():
    """
    Make sure we resolve nested refs gracefully and not get lost in
    the recursion. Also make sure we don't rely on dictionary order
    """
    os.environ["PYTHONHASHSEED"] = str(1)
    with open('tests/sample_schemas/nested_defns/swagger.yaml') as swagger_spec:
        spec_dict = yaml.safe_load(swagger_spec)
    spec = Spec.from_dict(spec_dict, '')
    assert spec.flattened_spec


def traverse_spec(swagger_spec):
    for k, v in swagger_spec.items():
        if k == "":
            raise Exception('Empty key detected in the swagger spec.')
        elif isinstance(v, dict):
            return traverse_spec(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    return traverse_spec(item)
    return


def test_extenal_refs_no_empty_keys():
    """
    This test ensures that we never use empty strings as
    keys swagger specs.
    """
    with open('tests/sample_schemas/external_refs/swagger.json') as swagger_spec:
        spec_dict = yaml.safe_load(swagger_spec)
    path = 'file:' + os.getcwd() + '/tests/sample_schemas/external_refs/swagger.json'
    spec = Spec.from_dict(spec_dict, path)
    flattened_spec = spec.flattened_spec
    traverse_spec(flattened_spec)
