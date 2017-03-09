.. pyramid_swagger documentation master file, created by
   sphinx-quickstart on Mon May 12 13:42:31 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pyramid_swagger's documentation!
===========================================

This project offers convenient tools for using `Swagger <http://swagger.io/getting-started/>`_ to define and validate
your interfaces in a `Pyramid <http://www.pylonsproject.org/>`_ webapp.

**You must supply** a working Pyramid application, and a Swagger schema describing your application's interface. In return, pyramid_swagger will provide:

* Request and response validation

* Swagger spec validation

* Automatically serving the swagger schema to interested clients (e.g. `Swagger UI <https://github.com/swagger-api/swagger-ui>`_)

pyramid_swagger works for both the 1.2 and 2.0 Swagger specifications, although users are strongly encouraged to use 2.0 going forward.

Contents:

.. toctree::
   :maxdepth: 1

   what_is_swagger
   quickstart
   changelog
   configuration
   migrating_to_swagger_20
   external_resources
   glossary
