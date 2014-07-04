Quickstart
===========================================

So let's get your pyramid app up and running!

The core steps to use pyramid_swagger are quite simple:

1. Create a Swagger API declaration for your service's endpoints
2. Add pyramid_swagger to your Pyramid application

Creating your first API declaration
-----------------------------------

Creating your initial API declaration can be intimidating but don't fear, it's not nearly as much work as it might initially appear.

To create your first API declaration, I encourage you to take a look at Swagger's official `PetStore example <http://petstore.swagger.wordnik.com>`_. You can even see the raw JSON for the associated API declarations, like the `Pet resource. <http://petstore.swagger.wordnik.com/api/api-docs/pet>`_. You'll notice that Swagger has a lot of details, but the core part of building a schema is documenting each endpoint's inputs and outputs.

For your intial attempt, documenting an endpoint can be simplified to some basic components:

1. Documenting the core URI (e.g. /foo/bar)
2. Documenting request parameters (in the path, in the query arguments, and in the query body)
3. Documenting the response

There are many other pieces of your REST interface that Swagger can describe, but these are the core components. The PetStore example has some good examples of all of these various types, so it can be a useful reference as you get used to the syntax.

For any questions about various details of documenting your interface with Swagger, you can consult the official `Swagger Spec <https://github.com/wordnik/swagger-spec/blob/master/versions/1.2.md>`_, although you may find it somewhat difficult to parse for use as anything but a reference.

You may find that the process of writing your API down in the Swagger format is surprisingly hard...this is good! It probably suggests that your API is not terribly well understood or maybe even underspecified right now. Anecdotally, users commonly report that writing their first Swagger api-docs has the unintended side effect of forcing them to reconsider exactly how their service should be interacting with the outside world -- a useful exercise!

Where to put your API declaration
-----------------------------------

Great, so we have one large JSON file containing our API declaration for all endpoints our service supports. Where do we put it?

The default location pyramid_swagger looks is the :samp:`swagger.json` file in the root of your application. In the event you want to configure this location, :doc:`see options here </configuration>`.

Add pyramid_swagger to your webapp
-----------------------------------

Last but not least, we need to turn on the pyramid_swagger library within your application. This is quite easy by default, either by augmenting your PasteDeploy .ini file, or by adding a line to your webapp method.

We'll show you the .ini method here, but you can read how to imperatively add the library to your app (and much more) in the :doc:`configuration page </configuration>` of these docs. For those using the .ini file, simply add the following line under your :samp:`[app:main]` section:

.. code-block:: ini

        [app:main]
        pyramid.includes = pyramid_swagger

With that, when your app starts you will get the benefit of:

* 4xx errors for requests not matching your schema
* 5xx errors for responses not matching your schema
* Automatic validation for correctness of your API declaration at application startup
