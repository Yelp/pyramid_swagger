Changelog
=========

2.6.0 (2017-11-14)
++++++++++++++++++++++++++
* Support setting bravado-core config values by prefixing them with ``bravado_core.`` in the pyramid_swagger config (see #221)
* Support raw_bytes response attribute, required for msgpack wire format support in outgoing responses (see #222)

2.5.0 (2017-10-26)
++++++++++++++++++++++++++
* Support `include_missing_properties` bravado-core flag in pyramid configuration
* Outsource flattening logic to bravado-core library.
* Expose bravado-core ``operation`` in request object
* Add ``pyramid_renderer`` and ``PyramidSwaggerRendererFactory``

2.4.1 (2017-06-14)
++++++++++++++++++++++++++
* Bugfix: add a quick fix to prevent resolve_refs from making empty json keys on external refs (see #206)

2.4.0 (2017-05-30)
++++++++++++++++++++++++++
* Bugfix: prevent resolve_refs from resolution failures when flattening specs with recursive $refs (see #204)
* Allow serving of api_docs from paths besides /api_docs (see #187)
* Support virtual hosting via SCRIPT_NAME (see #201 and https://www.python.org/dev/peps/pep-0333/)

2.3.2 (2017-04-10)
++++++++++++++++++
* Fix reading configuration values from INI files (see #182, #200)

2.3.1 (2017-03-27)
++++++++++++++++++
* Fix validation context for swagger 2.0 requests
* Added docs for validation context
* Preserved original exception when reraising for validation context exceptions
* Remove support for Python 2.6, newer Pyramid versions don't support it either
* Fix issue with missing content type when using webob >= 1.7 (see #185)

2.3.0 (2016-09-27)
++++++++++++++++++
* Fix installation with Python 3 on systems using a POSIX/ASCII locale.

2.3.0-rc3 (2016-06-28)
++++++++++++++++++++++
* Adds ``dereference_served_schema`` config flag to force served spec to be a
  single file. Useful for avoiding mixed-spec inconsistencies when running
  multiple versions of your service simultaneously.

2.3.0-rc2 (2016-05-09)
++++++++++++++++++++++
* Add ability for a single spec to serve YAML or JSON to clients
* Support multi-file local specs, serving them over multiple HTTP endpoints
* Improve Swagger validation messages when Pyramid cannot find your route (see #163)
* Bugfix: responses with headers in the spec no longer break request validation (see #159)

2.3.0-rc1 (2016-03-21)
++++++++++++++++++++++
* Support for YAML spec files
* Bugfix: remove extraneous x-scope in digested spec (see https://github.com/Yelp/bravado-core/issues/78)

2.2.3 (2016-02-09)
++++++++++++++++++++++
* Restore testing of py3x versions
* Support pyramid 1.6 and beyond.
* Support specification of routes using route_prefix

2.2.2 (2015-10-12)
++++++++++++++++++++++
* Upgrade to bravado-core 3.0.0, which includes a change in the way user-defined formats are registered. See the `Bravado 3.0.0 changelog entry`_ for more detail.

.. _Bravado 3.0.0 changelog entry: http://github.com/Yelp/bravado-core/blob/master/CHANGELOG.rst


2.2.1 (2015-08-20)
++++++++++++++++++++++
* No longer attempts to validate error responses, which typically don't follow
  the same format as successful responses. (Closes: #121)

2.2.0 (2015-08-19)
++++++++++++++++++++++
* Added ``prefer_20_routes`` configuration option to ease incremental migrations from v1.2 to
  v2.0. (See :ref:`prefer20migration`)

2.1.0 (2015-08-14)
++++++++++++++++++++++
* Added ``user_formats`` configuration option to provide user-defined formats which can be used for validations
  and conversions to wire-python-wire formats. (See :ref:`user-format-label`)
* Added support for relative cross-refs in Swagger v2.0 specs.

2.0.0 (2015-06-25)
++++++++++++++++++++++
* Added ``use_models`` configuration option for Swagger 2.0 backwards compatibility with existing pyramid views

2.0.0-rc2 (2015-05-26)
++++++++++++++++++++++
* Upgraded bravado-core to 1.0.0-rc1 so basePath is used when matching a request to an operation
* Updates for refactored SwaggerError exception hierarchy in bravado-core
* Fixed file uploads that use Content-Type: multipart/form-data

2.0.0-rc1 (2015-05-13)
++++++++++++++++++++++

**Backwards Incompatible**

* Support for Swagger 2.0 - See `Migrating to Swagger 2.0`_

.. _Migrating to Swagger 2.0: http://pyramid-swagger.readthedocs.org/en/latest/migrating_to_swagger_20.html

1.5.0 (2015-05-12)
++++++++++++++++++++++

* Now using swagger_spec_validator package for spec validation. Should be far
  more robust than the previous implementation.

1.5.0-rc2 (2015-04-1)
++++++++++++++++++++++

* Form-encoded bodies are now validated correctly.
* Fixed bug in `required` swagger attribute handling.

1.5.0-rc1 (2015-03-30)
++++++++++++++++++++++

* Added ``enable_api_docs_views`` configuration option so /api-docs
  auto-registration can be disabled in situations where users want to serve
  the Swagger spec in a nonstandard way.
* Added ``exclude_routes`` configuration option. Allows a blacklist of Pyramid
  routes which will be ignored for validation purposes.
* Added ``generate_resource_listing`` configuration option to allow
  pyramid_swagger to generate the ``apis`` section of the resource listing.
* Bug fix for issues relating to ``void`` responses (See `Issue 79`_)
* Added support for header validation.
* Make casted values from the request available through
  ``request.swagger_data``

.. _Issue 79: https://github.com/striglia/pyramid_swagger/issues/79

1.4.0 (2015-01-27)
++++++++++++++++++

* Added ``validation_context_path`` setting which allows the user to specify a
  path to a contextmanager to custom handle request/response validation
  exceptions.

1.3.0 (2014-12-02)
++++++++++++++++++

* Now throws RequestValidationError and ResponseValidationError instead of
  HTTPClientError and HTTPInternalServerError respectively. The new errors
  subclass the old ones for backwards compatibility.

1.2.0 (2014-10-21)
++++++++++++++++++

* Added ``enable_request_validation`` setting which toggles whether request
  content is validated.
* Added ``enable_path_validation`` setting which toggles whether HTTP calls to
  endpoints will 400 if the URL is not described in the Swagger schema. If this
  flag is disabled and the path is not found, no validation of any kind is
  performed by pyramid-swagger.
* Added ``exclude_paths`` setting which duplicates the functionality of
  `skip_validation`. `skip_validation` is deprecated and scheduled for removal
  in the 2.0.0 release.
* Adds LICENSE file
* Fixes misuse of webtest which could cause ``make test`` to pass while
  functionality was broken.

1.1.1 (2014-08-26)
++++++++++++++++++

* Fixes bug where response bodies were not validated correctly unless they were
  a model or primitive type.
* Fixes bug where POST bodies could be mis-parsed as query arguments.
* Better backwards compatibility warnings in this changelog!

1.1.0 (2014-07-14)
++++++++++++++++++

* Swagger schema directory defaults to ``api_docs/`` rather than being a required
  configuration line.
* If the resource listing or API declarations are not at the filepaths
  expected, readable errors are raised.
* This changelog is now a part of the build documentation and backfilled to the
  initial package version.


1.0.0 (2014-07-08)
++++++++++++++++++

**Backwards Incompatible**

* Initial fully functional release.
* Your service now must supply both a resource listing and all accompanying api
  declarations.
* Swagger schemas are automatically served out of ``/api-docs`` by including the
  library.
* The api declaration basepath returned by hitting ``/api-docs/foo`` is guaranteed
  to be ``Pyramid.request.application_url``.
* Void return types are now checked.


0.5.0 (2014-07-08)
++++++++++++++++++

* Added configurable list of regular expressions to not validate
  requests/responses against.
* Vastly improved documentation! Includes a quickstart for those new to the
  library.
* Adds coverage and code health badges to README


0.4.0 (2014-06-20)
++++++++++++++++++

* Request validation now works with path arguments.
* True acceptance testing implemented for all known features. Much improved
  coverage.

0.4.0 (2014-06-20)
++++++++++++++++++

* True acceptance testing implemented for all known features. Much improved
  coverage.

0.3.2 (2014-06-16)
++++++++++++++++++

* HEAD is now an allowed HTTP method

0.3.1 (2014-06-16)
++++++++++++++++++

* Swagger spec is now validated on startup
* Fixes bug where multiple methods with the same URL were not resolved properly
* Fixes bug with validating non-string args in paths and query args
* Fixes bug with referencing models from POST bodies

0.3.0 (2014-05-29)
++++++++++++++++++

* Response validation can be disabled via configuration
* Supports Python 3.3 and 3.4!

0.2.2 (2014-05-28)
++++++++++++++++++

* Adds readthedocs links, travis badge to README
* Requests missing bodies return 400 instead of causing tracebacks

0.2.1 (2014-05-15)
++++++++++++++++++

* Requests to non-existant endpoints now return 400 errors

0.1.1 (2014-05-13)
++++++++++++++++++

* Build docs now live at ``docs/build/html``

0.1.0 (2014-05-12)
++++++++++++++++++

* Initial version. Supports very basic validation of incoming requests.
