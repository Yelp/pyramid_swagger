# -*- coding: utf-8 -*-
from pyramid.httpexceptions import HTTPClientError, HTTPInternalServerError


class PyramidSwaggerRequestValidationError(HTTPClientError):
    pass


class PyramidSwaggerResponseValidationError(HTTPInternalServerError):
    pass
