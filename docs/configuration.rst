Configuring pyramid_swagger
===========================================

The pyramid_swagger library is intended to require very little configuration to
get up and running.

A few relevant settings for your `Pyramid .ini file <http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/environment.html#pyramid-includes-vs-pyramid-config-configurator-include>`_ (and their default settings):

.. code-block:: ini

        [app:main]
        # Add the pyramid_swagger validation tween to your app (required)
        pyramid.includes = pyramid_swagger

        # `api_docs.json` for Swagger 1.2 and/or `swagger.json` for Swagger 2.0
        # directory location.
        # Default: api_docs/
        pyramid_swagger.schema_directory = schemas/live/here

        # For Swagger 2.0, defines the relative file path (from
        # `schema_directory`) to get to the base swagger spec.
        # Supports JSON or YAML.
        #
        # Default: swagger.json
        pyramid_swagger.schema_file = swagger.json

        # Versions of Swagger to support. When both Swagger 1.2 and 2.0 are
        # supported, it is required for both schemas to define identical APIs.
        # In this dual-support mode, requests are validated against the Swagger
        # 2.0 schema only.
        # Default: 2.0
        # Supported versions: 1.2, 2.0
        pyramid_swagger.swagger_versions = 2.0

        # Check the correctness of Swagger spec files.
        # Default: True
        pyramid_swagger.enable_swagger_spec_validation = true

        # Check request content against Swagger spec.
        # Default: True
        pyramid_swagger.enable_request_validation = true

        # Check response content against Swagger spec.
        # Default: True
        pyramid_swagger.enable_response_validation = true

        # Check path is declared in Swagger spec.
        # If disabled and an appropriate Swagger schema cannot be
        # found, then request and response validation is skipped.
        # Default: True
        pyramid_swagger.enable_path_validation = true

        # Use Python classes instead of dicts to represent models in incoming
        # requests.
        # Default: False
        pyramid_swagger.use_models = false

        # Set value for property defined in swagger schema to None if value was not provided.
        # Skip property if value is missed and include_missing_properties is False.
        # Default: True
        pyramid_swagger.include_missing_properties = true

        # Exclude certain endpoints from validation. Takes a list of regular
        # expressions.
        # Default: ^/static/? ^/api-docs/? ^/swagger.json
        pyramid_swagger.exclude_paths = ^/static/? ^/api-docs/? ^/swagger.json

        # Exclude pyramid routes from validation. Accepts a list of strings
        pyramid_swagger.exclude_routes = catchall no-validation

        # Path to contextmanager to handle request/response validation
        # exceptions. This should be a dotted python name as per
        # http://docs.pylonsproject.org/projects/pyramid/en/latest/glossary.html#term-dotted-python-name
        # Default: None
        pyramid_swagger.validation_context_path = path.to.user.defined.contextmanager

        # Enable/disable automatic /api-doc endpoints to serve the swagger
        # schemas (true by default)
        pyramid_swagger.enable_api_doc_views = true

        # Base path for api docs (empty by default)
        # Examples:
        #   - leave empty and get api doc with GET /swagger.yaml
        #   - set to '/help' and get api doc with GET /help/swagger.yaml
        pyramid_swagger.base_path_api_docs = ''

        # Enable/disable generating the /api-doc endpoint from a resource
        # listing template (false by default). See `generate_resource_listing`
        # below for more details
        pyramid_swagger.generate_resource_listing = false

        # Enable/disable serving the dereferenced swagger schema in
        # a single http call. This can be slow for larger schemas.
        # Note: It is not suggested to use it with Python 2.6. Known issues with
        #       os.path.relpath could affect the proper behaviour.
        # Default: False
        pyramid_swagger.dereference_served_schema = false


.. note::

    ``pyramid_swawgger`` uses a ``bravado_core.spec.Spec`` instance for handling swagger related details.
    You can set `bravado-core config values <http://bravado-core.readthedocs.io/en/stable/config.html>`_ by adding a ``bravado-core.`` prefix to them.


Note that, equivalently, you can add these settings during webapp configuration:

.. code-block:: python

        def main(global_config, **settings):
            # ...
            settings['pyramid_swagger.schema_directory'] = 'schemas/live/here/'
            settings['pyramid_swagger.enable_swagger_spec_validation'] = True
            # ...and so on with the other settings...
            config = Configurator(settings=settings)
            config.include('pyramid_swagger')


.. _user-format-label:

user_formats (Swagger 2.0 only)
---------------------------------------

The option ``user_formats`` provides user defined formats which can be used
for validations/format-conversions. This options can only be used via webapp
configuration.

Sample usage:

.. code-block:: python

        def main(global_config, **settings):
            # ...
            settings['pyramid_swagger.user_formats'] = [user_format]


``user_format`` used above is an instance of
:class:`bravado_core.formatter.SwaggerFormat` and can be defined like this:

.. code-block:: python

        import base64
        from pyramid_swagger.tween import SwaggerFormat
        user_format = SwaggerFormat(format='base64',
                                    to_wire=base64.b64encode,
                                    to_python=base64.b64decode,
                                    validate=base64.b64decode,
                                    description='base64 conversions')


After defining this format, it can be used in the Swagger Spec definition like so:

.. code-block:: json

        {
            "name": "petId",
            "in": "path",
            "description": "ID of pet to return",
            "required": true,
            "type": "string",
            "format": "base64"
        }

.. note::

    The ``type`` need not be ``string`` always. The feature also works for other primitive
    types like integer, boolean, etc. More details are in the Swagger Spec v2.0 `Data Types`_.

    There are two types of validations which happen for user-defined formats.
    The first one is the usual type checking which is similarly done for all the other values.
    The second check is done by the ``validate`` function (from the ``user_format`` you configured for this type)
    which is run on the serialised format. If the value doesn't conform to the format, the
    ``validate`` function MUST raise an error and that error should be
    :class:`bravado_core.exception.SwaggerValidationError`.

    All the parameters to ``SwaggerFormat`` are mandatory. If you want any of the functions
    to behave as a no-op, assign them a value ``lambda x: x``. On providing a user-format, the
    default marshal/unmarshal behavior associated with that primitive type gets overridden by
    the ``to_wire``/``to_python`` behavior registered with that user-format, respectively.

.. _Data Types: https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#user-content-data-types

validation_context_path
-----------------------

Formatting validation errors for API requests/responses to fit every possible
swagger spec and response type is very complicated and will never cover every
scenario. The ``validation_context_path`` option provides a way to change or
format the response returned when :mod:`pyramid_swagger` validation fails.

Sample usage:

.. code-block:: python

        from pyramid_swagger import exceptions

        class UserDefinedResponseError(Exception):
            pass

        def validation_context(request, response=None):
            try:
                yield
            except exceptions.RequestValidationError as e:
                # Content type will be application/json instead of plain/text
                raise exceptions.RequestValidationError(json=[str(e)])

            except exceptions.ResponseValidationError as e:
                # Reraise as non-pyramid exception
                raise UserDefinedResponseError(str(e))



The errors that are raised from the validation_context are defined in
:mod:`pyramid_swagger.exceptions`.

.. note::

    By default :mod:`pyramid_swagger` validation errors return content type plain/text

generate_resource_listing (Swagger 1.2 only)
--------------------------------------------

With a large API (many Resource objects) the boilerplate ``apis`` field of
the `Resource Listing`_ document can become painful to maintain. This
setting provides a way to relieve that burden.

When the ``generate_resource_listing`` option is enabled
:mod:`pyramid_swagger` will automatically generate the ``apis`` section of
the swagger `Resource Listing`_ from the list of ``*.json`` files in the
schema directory. The ``apis`` listing is generated by using the name of the
file (without the extension) as the ``path``.

To use this feature, create an ``api_docs.json`` file in the schema directory.
This file may contain any relevant field from `Resource Listing`_,
but it **must** exclude the ``apis`` field. In many cases this
``api_docs.json`` will only contain a single key ``swaggerVersion: 1.2``.

.. _Resource Listing: https://github.com/swagger-api/swagger-spec/blob/master/versions/1.2.md#user-content-51-resource-listing

.. note::

    Generated `Resource Listing`_ documents will not have the optional
    ``description`` field.

Example
~~~~~~~

Given a schema directory with the following files

.. code-block:: none

    api_docs/
    ├── api_docs.json
    ├── pet.json
    ├── store.json
    └── user.json

Previously you might have created an ``api_docs.json`` that looked like this

.. code-block:: json

    {
        "swaggerVersion": "1.2",
        "apiVersion": "1.0",
        "apis": [
            {
                "path": "/pet",
            },
            {
                "path": "/store",
            },
            {
                "path": "/user",
            },
        ]
    }

When ``generate_resource_listing`` is enabled, the ``api_docs.json`` should
be similar, but with the ``apis`` section removed.

.. code-block:: json

    {
        "swaggerVersion": "1.2",
        "apiVersion": "1.0",
    }

:mod:`pyramid_swagger` will generate a `Resource Listing`_ which is equivalent
to the original ``api_docs.json`` with a full ``apis`` list.
