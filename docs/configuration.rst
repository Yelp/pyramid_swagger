Configuring pyramid_swagger
===========================================

By default, pyramid_swagger assumes your swagger spec is available at
"swagger.json" in the project's root, although you are free to configure this
location via Pyramid's registry.

A few relevant settings for your PasteDeploy .ini file:::

        [app:main]
        # Add the pyramid_swagger request validation tween to your app
        pyramid.includes = pyramid_swagger

        # Point pyramid_swagger at your swagger spec (defaults to swagger.json)
        pyramid_swagger.schema_path = "swagger.json"

        # Enable/disable response validation (off by default)
        pyramid_swagger.enable_response_validation = true

        # Enable/disable swagger spec validation (on by default)
        pyramid_swagger.enable_swagger_spec_validation = true

note that, equivalently, you can add these from your webapp:::

        def main(global_config, **settings):
            # ...
            settings['pyramid_swagger.enable_response_validation'] = True
            settings['pyramid_swagger.schema_path'] = 'swagger.json'
            config = Configurator(settings=settings)
            config.include('pyramid_swagger')
