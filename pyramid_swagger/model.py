# -*- coding: utf-8 -*-
"""
The core model we use to represent the entire ingested swagger schema for this
service.
"""
from __future__ import absolute_import

from collections import namedtuple


PyramidEndpoint = namedtuple(
    'PyramidEndpoint',
    'path route_name view renderer')


class PathNotMatchedError(Exception):
    """Raised when a SwaggerSchema object is given a request it cannot match
    against its stored schema."""
    pass
