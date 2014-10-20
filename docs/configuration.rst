Configuring pyramid_swagger
===========================================

The pyramid_swagger library is intended to require very little configuration to
get up and running.

A few relevant settings for your `Pyramid .ini file <http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/environment.html#pyramid-includes-vs-pyramid-config-configurator-include>`_ (and their default settings):

.. code-block:: ini

        [app:main]
        # Add the pyramid_swagger validation tween to your app (required)
        pyramid.includes = pyramid_swagger

        # Point pyramid_swagger at the directory containing your api_docs.json ('api_docs/' by default)
        pyramid_swagger.schema_directory = "schemas/live/here"

        # Enable/disable response validation (true by default)
        pyramid_swagger.enable_response_validation = true

        # Enable/disable minimal check if Swagger spec is correct (true by default)
        pyramid_swagger.enable_swagger_spec_validation = true

        # Enable/disable check if path is declared in Swagger spec (true by default)
        pyramid_swagger.enable_path_validation = True

        # Exclude certain endpoints from validation. Takes a list of regular
        # expressions.
        pyramid_swagger.exclude_paths = [r'^/static/?', r'^/api-docs/?']

Note that, equivalently, you can add these during webapp configuration:

.. code-block:: python

        def main(global_config, **settings):
            # ...
            settings['pyramid_swagger.schema_directory'] = 'schemas/live/here/'
            settings['pyramid_swagger.enable_response_validation'] = True
            settings['pyramid_swagger.enable_swagger_spec_validation'] = True
            settings['pyramid_swagger.exclude_paths'] = [r'^/static/?', r'^/api-docs/?']
            config = Configurator(settings=settings)
            config.include('pyramid_swagger')
