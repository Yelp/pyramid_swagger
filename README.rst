pyramid_swagger
=======================

This project offers convenient tools for using Swagger to define and validate
your interfaces in a Pyramid webapp.

In particular, in currently offers two main features:

* Request validation (and automatic 4xx errors) via a pyramid tween
* A method for pyramid response validation

Each assumes your swagger spec is available at "swagger.json" in the project's
root, although you are free to configure this location via Pyramid's registry.
