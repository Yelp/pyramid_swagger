# -*- coding: utf-8 -*-
import sys

from pyramid.httpexceptions import HTTPClientError, HTTPInternalServerError


class RequestValidationError(HTTPClientError):
    pass


class ResponseValidationError(HTTPInternalServerError):
    pass


def wrap_exception(exception_class):
    def generic_exception(method):
        def wrapper(*args, **kwargs):
            try:
                method(*args, **kwargs)
            except Exception as e:
                raise exception_class(str(e)), None, sys.exc_info()[2]
        return wrapper
    return generic_exception
