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
      ...
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
