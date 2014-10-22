Configuring pyramid_swagger
===========================================

The pyramid_swagger library is intended to require very little configuration to
get up and running.

A few relevant settings for your `Pyramid .ini file <http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/environment.html#pyramid-includes-vs-pyramid-config-configurator-include>`_ (and their default settings):

.. code-block:: ini

        [app:main]
        # Add the pyramid_swagger validation tween to your app (required)
        pyramid.includes = pyramid_swagger

        # `api_docs.json` directory location.
        # Default: 'api_docs/'
        pyramid_swagger.schema_directory = "schemas/live/here"

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
        pyramid_swagger.enable_path_validation = True

        # Exclude certain endpoints from validation. Takes a list of regular
        # expressions.
        # Default: [r'^/static/?', r'^/api-docs/?']
        pyramid_swagger.exclude_paths = [r'^/static/?', r'^/api-docs/?']

Note that, equivalently, you can add these during webapp configuration:

.. code-block:: python

        def main(global_config, **settings):
            # ...
            settings['pyramid_swagger.schema_directory'] = 'schemas/live/here/'
            settings['pyramid_swagger.enable_swagger_spec_validation'] = True
            # ...and so on with the other settings...
            config = Configurator(settings=settings)
            config.include('pyramid_swagger')
