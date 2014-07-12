Changes
=======

0.5.0 (2014-07-08)
++++++++++++++++

* Added configurable list of regular expressions to not validate
  requests/responses against.
* Vastly improved documentation! Includes a quickstart for those new to the
  library.
* Adds coverage and code health badges to README


0.4.0 (2014-06-20)
++++++++++++++++

* Request validation now works with path arguments.
* True acceptance testing implemented for all known features. Much improved
  coverage.

0.4.0 (2014-06-20)
++++++++++++++++

* True acceptance testing implemented for all known features. Much improved
  coverage.

0.3.2 (2014-06-16)
++++++++++++++++

* HEAD is now an allowed HTTP method

0.3.1 (2014-06-16)
++++++++++++++++

* Swagger spec is now validated on startup
* Fixes bug where multiple methods with the same URL were not resolved properly
* Fixes bug with validating non-string args in paths and query args
* Fixes bug with referencing models from POST bodies

0.3.0 (2014-05-29)
++++++++++++++++

* Response validation can be disabled via configuration
* Supports Python 3.3 and 3.4!

0.2.2 (2014-05-28)
++++++++++++++++

* Adds readthedocs links, travis badge to README
* Requests missing bodies return 400 instead of causing tracebacks

0.2.1 (2014-05-15)
++++++++++++++++

* Requests to non-existant endpoints now return 400 errors

0.1.1 (2014-05-13)
++++++++++++++++

* Build docs now live at docs/build/html

0.1.0 (2014-05-12)
++++++++++++++++

* Initial version. Supports very basic validation of incoming requests.
