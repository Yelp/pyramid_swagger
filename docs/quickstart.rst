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

For your intial attempt, documenting an endpoint can be simplified to some basic components:

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
    ``pyramid_swawgger.enable_request_validation`` is enabled.

Accessing Swagger Operation
---------------------------

During the implementation of an endpoint you could eventually have need of accessing the Swagger Specs that defined that specific view.
``pyramid_swagger`` will inject in the request object a new property (that will be evaluated only if accessed) called ``operation``.

``request.operation`` will be set to ``None`` for Swagger 1.2 defined endpoints, while it will be an `Operation <https://github.com/Yelp/bravado-core/blob/v4.8.4/bravado_core/operation.py#L12>`_ object if the endpoint is defined by Swagger 2.0 specs.

Set pyramid view renderer
-------------------------

Using :mod:`pyramid_swagger` you will get automatic conversions between input JSON objects to easy to handle python objects.
An example could be a swagger object property marked to use date property, the library will take care of converting the ISO 8601 date representation to an easy to handle python ``datetime.date`` object.

Usually, while building the views that returns object that needs special handling (like ``datetime.date``) you are *forced* to perform manual operations to convert the python object on objects that could be serialized with the default ``pyramid`` renderers (ie. ``pyramid.`renderers.JSON``).
Using ``pyramid_swagger.renderer.PyramidSwaggerRendererFactory`` as base renderer for your pyramid view will remove this *human intervention*, so you can focus more on defining the internal logic respect dealing with formatting.

Here is an example:

Let's assume that you have the following specs

.. code-block:: json

    {
      "definitions": {
        "json_object": {
          "maxProperties": 1,
          "minProperties": 1,
          "properties": {
            "date": {
              "type": "string",
              "format": "date"
            },
            "date-time": {
              "type": "string",
              "format": "date-time"
            }
          },
          "type": "object"
        }
      },
      "paths": {
        "/echo_date": {
          "post": {
            "description": "Echoes the input date into response body",
            "parameters": [
              {
                "format": "date",
                "in": "formData",
                "name": "date",
                "type": "string"
              }
            ],
            "operationId": "echo_date",
            "responses": {
              "200": {
                "$ref": "#/responses/200_ok"
              }
            }
          }
        },
        "/echo_date_time": {
          "post": {
            "description": "Echoes the input date-time into response body",
            "operationId": "echo_date_time",
            "parameters": [
              {
                "format": "date-time",
                "in": "formData",
                "name": "date_time",
                "type": "string"
              }
            ],
            "responses": {
              "200": {
                "$ref": "#/responses/200_ok"
              }
            }
          }
        }
      },
      "responses": {
          "200_ok": {
            "description": "HTTP/200 OK",
            "schema": {
            "$ref": "#/definitions/json_object"
          }
      },
      "swagger": "2.0"
    }

and that your views are defined as

.. code-block:: python

    @view_config(route_name='echo_date', renderer='pyramid_swagger')
    def echo_date(request):
        input_date = request.swagger_data['date']
        assert isinstance(input_date, datetime.date)
        return {'date': input_date}

    @view_config(route_name='echo_date_time', renderer='json')
    def echo_date(request):
        input_date_time = request.swagger_data['date_time']
        assert isinstance(input_date_time, datetime.datetime)
        return {'date-time': input_date_time}

Calling the ``/echo_date`` endpoint you will receive, as expected, a response that will look like ``{"date": "2017-09-06"}``, while calling ``/echo_date_time`` endpoint you will receive an unexpected HTTP/500 as response.

This happens because ``pyramid_swagger`` renderer performs the proper object unmarshalling (transforming the ``datetime.date`` object to an ISO 8601 string representation) before calling the base JSON renderer; while the default ``json`` renderer, which is not capable to transform to JSON a ``datetime.datetime`` object, will raise an exception.

To workaround the limitation introduced by ``json`` formatter the developer has to *manually*  convert the ``datetime.datetime`` object to the desired string representation or adding `adapters <https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/renderers.html#using-the-add-adapter-method-of-a-custom-json-renderer>`_ for the types not handled by ``json`` renderer.
Either approaches are introducing an additional complexity on the service developer since he/she has to care about response formatting and could not be compliant with the service specification.

In order to increase the flexibility of the new rendering feature, it is exposed ``PyramidSwaggerRendererFactory`` class which will allow you to define your own custom renderer.
The defined renderer will operate on the marshaled, according to the Swagger Specification, response.

Example of definition of a custom renderer

.. code-block:: python

    class MyPersonalRendererFactory(object):
        def __init__(self, info):
            # Initialize your factory
            pass

        def __call__(self, value, system):
            # perform your personal rendering operations
            # you can assume that value is a marshaled response, so already JSON serializable object
            return rendered_value

Once you have defined your own renderer you have to wrap the new renderer in ``PyramidSwaggerRendererFactory`` and register it to the pyramid framework as described by `Adding and Changing Renderers pyramid documentation <https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/renderers.html#adding-and-changing-renderers>`_.

.. code-block:: python

    config.add_renderer(name='custom_renderer', factory=PyramidSwaggerRendererFactory(MyPersonalRendererFactory))
