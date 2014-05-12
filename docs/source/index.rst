.. pyramid_swagger documentation master file, created by
   sphinx-quickstart on Mon May 12 13:42:31 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pyramid_swagger's documentation!
===========================================

This project offers convenient tools for using Swagger to define and validate
your interfaces in a Pyramid webapp.

In particular, in currently offers two main features:

* Request validation (and automatic 4xx errors) via a pyramid tween * A method
  for pyramid response validation

Each assumes your swagger spec is available at "swagger.json" in the project's
root, although you are free to configure this location via Pyramid's registry.

To include the tween in your pyramid app, insert this into your PasteDeploy
.ini file:::

        [app:main] pyramid.includes = pyramid_swagger.tweens

or, equivalently, add this to your webapp:::

        config = Configurator(settings=settings) # ...
        config.include('pyramid_swagger')


For response validation, see the validate_outgoing_response method in the
pyramid_swagger.tweens module.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

