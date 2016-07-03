# -*- coding: utf-8 -*-
from bravado_core.spec import Spec
import pytest

from six.moves.urllib.parse import urlparse

from pyramid_swagger.api import _get_target, _marshal_target, _unmarshal_target


@pytest.fixture
def bravado_spec():
    return Spec(
        spec_dict={},
        origin_url='/swagger.json',
    )


@pytest.mark.parametrize(
    'target',
    [
        'file:///dir1/dir2/file.json#/path1/path2/resource',
        'dir1/dir2/file.json#/path1/path2/resource',
        'http://hostname/dir1/dir2/file.json#/path1/path2/resource',
        'https://hostname/dir1/dir2/file.json#/path1/path2/resource',
    ]
)
def test_marshaller_not_raises(target):
    assert target == _unmarshal_target(_marshal_target(urlparse(target)))


@pytest.mark.parametrize(
    'target',
    [
        '',
        'xhttps://hostname/dir1/dir2/file.json#/path1/path2/resource',
    ]
)
def test_marshaller_raises(target):
    with pytest.raises(ValueError):
        _marshal_target(urlparse(target))


@pytest.mark.parametrize(
    'target',
    [
        'xhttps.hostname..dir1..dir2..file.json|..path1..path2..resource',
    ]
)
def test_unmarshaller_raises(target):
    with pytest.raises(ValueError):
        _unmarshal_target(target)


@pytest.mark.parametrize(
    'current_path, target, expected',
    [
        (
            # with url it should be the same
            'swagger.json',
            'http://hostname/dir1/dir2/file.json#/path1/path2/resource',
            'http://hostname/dir1/dir2/file.json#/path1/path2/resource',
        ),
        (
            # relative directory respect to the swagger file
            '/dir1/another1.json',
            '../dir2/other2.json#/path/resource',
            'dir2/other2.json#/path/resource',
        ),
        (
            'file:///swagger.json',
            '#/path/resource',
            'swagger.json#/path/resource',
        ),
    ]
)
def test_target(bravado_spec, current_path, target, expected):
    assert \
        _get_target(bravado_spec, target, current_path) == urlparse(expected)


@pytest.mark.parametrize(
    'target',
    [
        '',
        'xhttps://hostname/dir1/dir2/file.json#/path1/path2/resource',
    ]
)
def test_target_raises(bravado_spec, target):
    with pytest.raises(ValueError):
        _get_target(bravado_spec, target)
