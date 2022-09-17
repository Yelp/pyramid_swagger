Quickstart
==========

So let's get your pyramid app up and running!

The core steps to use pyramid_swagger are quite simple:

1. Create a Swagger Schema for your service's endpoints
2. Add pyramid_swagger to your Pyramid application

Creating your first Swagger Schema
-----------------------------------

Creating your initial Swagger Schema can be intimidating but don't fear, it's not nearly as much work as it might initially appear.

To create your first Swagger Schema, I encourage you to take a look at Swagger's official `PetStore example <http://petstore.swagger.io>`_. You can even see the raw JSON for the `Swagger Schema. <http://petstore.swagger.io/v2/swagger.json>`_ You'll notice that Swagger has a lot of details, but the core part of building a schema is documenting each endpoint's inputs and outputs.

For your initial attempt, documenting an endpoint can be simplified to some basic components:

1. Documenting the core URI (e.g. /foo/bar)
2. Documenting request parameters (in the path, in the query arguments, and in the query body)
3. Documenting the response

There are many other pieces of your REST interface that Swagger can describe, but these are the core components. The PetStore example has some good examples of all of these various types, so it can be a useful reference as you get used to the syntax.

For any questions about various details of documenting your interface with Swagger, you can consult the official `Swagger Spec <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md>`_, although you may find it somewhat difficult to parse for use as anything but a reference.

You may find that the process of writing your API down in the Swagger format is surprisingly hard...this is good! It probably suggests that your API is not terribly well understood or maybe even underspecified right now. Anecdotally, users commonly report that writing their first Swagger api-docs has the unintended side effect of forcing them to reconsider exactly how their service should be interacting with the outside world -- a useful exercise!

Where to put your Swagger Schema
---------------------------------

Great, so we have one large JSON file containing our API declaration for all endpoints our service supports. What now?

Now place the Swagger Schema in :samp:`api_docs/swagger.json`. The path has no relation to the paths described in your API declaration, it is only used internally to help Swagger discover your schemas.

Add pyramid_swagger to your webapp
----------------------------------

Last but not least, we need to turn on the pyramid_swagger library within your application. This is quite easy by default, either by augmenting your PasteDeploy .ini file, or by adding a line to your webapp method.

We'll show you the .ini method here, but you can read how to imperatively add the library to your app (and much more) in the :doc:`configuration page </configuration>` of these docs. For those using the .ini file, simply add the following line under your :samp:`[app:main]` section:

.. code-block:: ini

        [app:main]
        pyramid.includes = pyramid_swagger

With that, when your app starts you will get the benefit of:

* 4xx errors for requests not matching your schema
* 5xx errors for responses not matching your schema
* Automatic validation for correctness of your Swagger Schema at application startup
* Automatic serving of your Swagger Schema from the /swagger.json endpoint

Update the routes
-----------------

For each of the routes declared in your swagger.json, you need to add the route to the Pyramid dispatch using traditional methods. For example, in your __init__.py:

.. code-block:: python

    def main(global_config, **settings):
        """ This function returns a Pyramid WSGI application.
        """
        config = Configurator(settings=settings)
        config.include('pyramid_chameleon')
        config.add_static_view('static', 'static', cache_max_age=3600)
        config.add_route('api.things.get', '/api/things', request_method='GET')
        #
        # Additional routes go here
        #
        config.scan()
        return config.make_wsgi_app()

Accessing request data
----------------------

Now that :mod:`pyramid_swagger` is enabled you can create a view. All the
values that are specified in the Swagger Schema for an endpoint are available
from a single :class:`dict` on the request  ``request.swagger_data``. These
values are casted to the type specified by the Swagger Schema.

Example:

.. code-block:: python

    from pyramid.view import view_config

    @view_config(route_name='api.things.get')
    def get_things(request):
        # Returns thing_id as an int (assuming the swagger type is integer)
        thing_id = request.swagger_data['thing_id']
        ...
        return {...}


The raw values (not-casted to any type) are still available from their
usual place on the request (`matchdict`, `GET`, `POST`, `json()`, etc)

If you have ``pyramid_swagger.use_models`` set to true, you can interact with
models defined in ``#/definitions`` as Python classes instead of dicts.

.. code-block:: json

    {
      "swagger": "2.0",
      "definitions": {
        "User": {
          "type": "object",
          "properties": {
            "first_name": {
              "type": "string"
            },
            "last_name": {
              "type": "string"
            }
          }
        }
      }
    }

.. code-block:: python

    @view_config(route_name='add.user')
    def add_user(request):
        user = request.swagger_data['user']
        assert isinstance(user, bravado_core.models.User)
        first_name = user.first_name
        ...

Otherwise, models are represented as dicts.

.. code-block:: python

    @view_config(route_name='add.user')
    def add_user(request):
        user = request.swagger_data['user']
        assert isinstance(user, dict)
        first_name = user['first_name']
        ...

.. note::

    Values in ``request.swagger_data`` are only available if
    ``pyramid_swagger.enable_request_validation`` is enabled.

Accessing Swagger Operation
---------------------------

During the implementation of an endpoint you could eventually have need of accessing the Swagger Specs that defined that specific view.
``pyramid_swagger`` will inject in the request object a new property (that will be evaluated only if accessed) called ``operation``.

``request.operation`` will be set to ``None`` for Swagger 1.2 defined endpoints, while it will be an `Operation <https://github.com/Yelp/bravado-core/blob/v4.8.4/bravado_core/operation.py#L12>`_ object if the endpoint is defined by Swagger 2.0 specs.

pyramid_swagger renderer
------------------------

Using :mod:`pyramid_swagger` you will get automatic conversions of the input JSON objects to easy to handle python objects.
An example could be a swagger object string property using the ``date`` format , the library will take care of converting the
ISO 8601 date representation to an easy to handle python ``datetime.date`` object.

While defining the :mod:`pyramid` view that will handle the endpoint you have to make sure that the chosen renderer will be able to
properly render your response. In the case of an endpoint that returns *objects* that requires a special handling
(like ``datetime.date``) the developer is *forced* to:

* manually convert the python object to an object that could be handled by the renderer
* add an `adapter <https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/renderers.html#using-the-add-adapter-method-of-a-custom-json-renderer>`_ for instructing pyramid to handle your object
* define a custom renderer that is able to properly serialize the object

:mod:`pyramid_swagger` provides:

* a new renderer, called ``pyramid_swagger``
* a new renderer renderer factory, called ``pyramid_swagger.renderer.PyramidSwaggerRendererFactory``

----------------------------------
How pyramid_swagger renderer works
----------------------------------

The new :mod:`pyramid_swagger` renderer is a wrapper around the default ``pyramid.renderers.JSON`` renderer.

:mod:`pyramid_swagger` will receive, from your pyramid view, the object that has to be rendered, perform the marshaling operations and then call the default JSON renderer.

.. note::
    The usage of this renderer allows to get full support of `custom formats <configuration.html#user-formats-swagger-2-0-only>`_


Let's assume that your view returns ``{'date': datetime.date.today()}`` and that your response spec is similar to

.. code-block:: json

    {
        "200": {
            "description": "HTTP/200",
            "schema": {
                "properties": {
                    "date": {
                        "type": "string",
                        "format": "date"
                    }
                }
            }
        }
    }


If your view is configured to use ``json`` renderer then your endpoint will surprisingly return HTTP/500 errors.
The errors are caused by the fact that ``pyramid.renderers.JSON`` is not aware on how to convert a ``datetime.date`` object.

If your view is configured to use ``pyramid_swagger`` renderer then your endpoint will provide HTTP/200 responses similar
to ``{"date": "2017-09-16"}``.

This is possible because the marshalling of the view return value converts the ``datetime.date`` object to its ISO 8601
string representation that could be handled by the default JSON renderer.

.. note::

    The marshaling operation will be performed according to the specific response schema defined for the particular endpoint.
    It means that if your response doesn't specify a field it will be transparently passed to the wrapped renderer.


---------------------------------------
How PyramidSwaggerRendererFactory works
---------------------------------------

``PyramidSwaggerRendererFactory`` allows you to create a custom renderer that operates on the marshaled result from your view.

The defined renderer will operate on the marshaled, according to the Swagger Specification, response.

Example of definition of a custom renderer

.. code-block:: python

    class MyPersonalRendererFactory(object):
        def __init__(self, info):
            # Initialize your factory (refer to standard documentation for more information)
            pass

        def __call__(self, value, system):
            # ``value`` contain the marshaled representation of the object returned by your view.
            # If your view is returning a ``datetime.date`` object for a field with date format
            # you can assume that the field has already been converted to its ISO 8601 representation

            # perform your personal rendering operations
            # you can assume that value is a marshaled response, so already JSON serializable object
            return rendered_value

Once you have defined your own renderer you have to wrap the new renderer in ``PyramidSwaggerRendererFactory`` and register it to the pyramid framework as described by `Adding and Changing Renderers pyramid documentation <https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/renderers.html#adding-and-changing-renderers>`_.

.. code-block:: python

    config.add_renderer(name='custom_renderer', factory=PyramidSwaggerRendererFactory(MyPersonalRendererFactory))
