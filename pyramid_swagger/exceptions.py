# -*- coding: utf-8 -*-
import sys

import six
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.httpexceptions import HTTPNotFound


class RequestValidationError(HTTPBadRequest):
    def __init__(self, *args, **kwargs):
        self.child = kwargs.pop('child', None)
        super(RequestValidationError, self).__init__(*args, **kwargs)


class PathNotFoundError(HTTPNotFound):
    def __init__(self, *args, **kwargs):
        self.child = kwargs.pop('child', None)
        super(PathNotFoundError, self).__init__(*args, **kwargs)


class ResponseValidationError(HTTPInternalServerError):
    def __init__(self, *args, **kwargs):
        self.child = kwargs.pop('child', None)
        super(ResponseValidationError, self).__init__(*args, **kwargs)


def wrap_exception(exception_class):
    def generic_exception(method):
        def wrapper(*args, **kwargs):
            try:
                method(*args, **kwargs)
            except Exception as e:
                six.reraise(
                    exception_class,
                    exception_class(str(e)),
                    sys.exc_info()[2])
        return wrapper
    return generic_exception
