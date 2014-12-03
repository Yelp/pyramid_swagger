# -*- coding: utf-8 -*-
from pyramid.httpexceptions import HTTPClientError, HTTPInternalServerError


class RequestValidationError(HTTPClientError):
    pass


class ResponseValidationError(HTTPInternalServerError):
    pass
