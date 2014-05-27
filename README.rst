[![Build Status](https://travis-ci.org/striglia/pyramid_swagger.png)](https://travis-ci.org/striglia/pyramid_swagger)


pyramid_swagger
=======================

This project offers convenient tools for using Swagger to define and validate
your interfaces in a Pyramid webapp.

In particular, in currently offers two main features:

* Request validation (and automatic 4xx errors) via a pyramid tween
* A method for pyramid response validation

Each assumes your swagger spec is available at "swagger.json" in the project's
root, although you are free to configure this location via Pyramid's registry.

To include the tween in your pyramid app, insert this into your PasteDeploy
.ini file:

```
[app:main]
pyramid.includes = pyramid_swagger
```

or, equivalently, add this to your webapp:

```
config = Configurator(settings=settings)
# ...
config.include('pyramid_swagger')
```

Full documentation is available at https://readthedocs.org/projects/pyramid-swagger/
