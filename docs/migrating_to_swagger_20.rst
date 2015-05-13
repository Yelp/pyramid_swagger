Migrating to Swagger 2.0
========================

So you're using pyramid_swagger with Swagger 1.2 and now it is time to upgrade to Swagger 2.0.

Just set the version of Swagger to support via configuration like so:

.. code-block:: ini

        [app:main]
        pyramid_swagger.swagger_versions = ['2.0']

If you would like to continue servicing Swagger 1.2 clients, pyramid_swagger has you covered.

.. code-block:: ini

        [app:main]
        pyramid_swagger.swagger_versions = ['1.2', '2.0']

.. note::

    When both versions of Swagger are supported, all requests are validated against the 2.0 version of the schema.
    Make sure that your 1.2 and 2.0 schemas define an identical set of APIs.

If you're not using an ini file, configuration in Python also works.

.. code-block:: python

    def main(global_config, **settings):
        # ...
        settings['pyramid_swagger.swagger_versions'] = ['2.0']
        # ...and so on with the other settings...
        config = Configurator(settings=settings)
        config.include('pyramid_swagger')

Next, place your Swagger 2.0 schema ``swagger.json`` file in the same directory as your Swagger 1.2 schema and you're ready to go.
