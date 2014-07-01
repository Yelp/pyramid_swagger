Configuring pyramid_swagger
===========================================

The pyramid_swagger library is intended to require very little configuration to
get up and running.

Currently, pyramid_swagger assumes your api declaration is available at
"swagger.json" in the project's root, although you are free to configure this
location via Pyramid's registry.

A few relevant settings for your PasteDeploy .ini file:

.. code-block:: ini

        [app:main]
        # Add the pyramid_swagger validation tween to your app (minimum required)
        pyramid.includes = pyramid_swagger

        # Point pyramid_swagger at your api declaration (defaults to swagger.json)
        pyramid_swagger.schema_path = "swagger.json"

        # Enable/disable response validation (false by default)
        pyramid_swagger.enable_response_validation = true

        # Enable/disable swagger spec validation (true by default)
        pyramid_swagger.enable_swagger_spec_validation = true

note that, equivalently, you can add these during webapp configuration:

.. code-block:: python

        def main(global_config, **settings):
            # ...
            settings['pyramid_swagger.enable_response_validation'] = True
            settings['pyramid_swagger.schema_path'] = 'swagger.json'
            config = Configurator(settings=settings)
            config.include('pyramid_swagger')
