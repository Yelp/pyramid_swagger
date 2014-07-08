Configuring pyramid_swagger
===========================================

The pyramid_swagger library is intended to require very little configuration to
get up and running.

A few relevant settings for your `Pyramid .ini file <http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/environment.html#pyramid-includes-vs-pyramid-config-configurator-include>`_ (and their default settings):

.. code-block:: ini

        [app:main]
        # Add the pyramid_swagger validation tween to your app (required)
        pyramid.includes = pyramid_swagger

        # Point pyramid_swagger at your api declaration (defaults to swagger.json)
        pyramid_swagger.schema_path = "swagger.json"

        # Enable/disable response validation (true by default)
        pyramid_swagger.enable_response_validation = true

        # Enable/disable swagger spec validation (true by default)
        pyramid_swagger.enable_swagger_spec_validation = true

        # Skip validation for certain endpoints. Takes a list
        # of regular expressions for the endpoints to skip
        # Note: This are not raw strings, hence the double '\'
        # (/(static)\\b, /(api-docs)\\b by default)
        pyramid_swagger.skip_validation = /(static)\\b
                                          /(api-docs)\\b

Note that, equivalently, you can add these during webapp configuration:

.. code-block:: python

        def main(global_config, **settings):
            # ...
            settings['pyramid_swagger.schema_path'] = 'swagger.json'
            settings['pyramid_swagger.enable_response_validation'] = True
            settings['pyramid_swagger.enable_swagger_spec_validation'] = True
            settings['pyramid_swagger.skip_validation'] = [r'/(static)\b', r'/(api-docs)\b']
            config = Configurator(settings=settings)
            config.include('pyramid_swagger')
