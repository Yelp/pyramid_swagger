# -*- coding: utf-8 -*-
import sys

import six
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.httpexceptions import HTTPNotFound


class RequestValidationError(HTTPBadRequest):
    pass


class ResourceNotFound(HTTPNotFound):
    pass


class ResponseValidationError(HTTPInternalServerError):
    pass


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
