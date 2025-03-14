---
---

# OpenApiLibCore for Robot Framework

The OpenApiLibCore library is a utility library that is meant to simplify creation
of other Robot Framework libraries for API testing based on the information in
an OpenAPI document (also known as Swagger document).
This document explains how to use the OpenApiLibCore library.

My RoboCon 2022 talk about OpenApiDriver and OpenApiLibCore can be found [here](https://www.youtube.com/watch?v=7YWZEHxk9Ps)

For more information about Robot Framework, see http://robotframework.org.

---

> Note: OpenApiLibCore is still being developed so there are currently
restrictions / limitations that you may encounter when using this library to run
tests against an API. See [Limitations](#limitations) for details.

---

## Installation

If you already have Python >= 3.8 with pip installed, you can simply run:

`pip install --upgrade robotframework-openapi-libcore`

---

## OpenAPI (aka Swagger)

The OpenAPI Specification (OAS) defines a standard, language-agnostic interface
to RESTful APIs, see https://swagger.io/specification/

The OpenApiLibCore implements a number of Robot Framework keywords that make it
easy to interact with an OpenAPI implementation by using the information in the
openapi document (Swagger file), for examply by automatic generation of valid values
for requests based on the schema information in the document.

> Note: OpenApiLibCore is designed for APIs based on the OAS v3
The library has not been tested for APIs based on the OAS v2.

---

## Getting started

Before trying to use the keywords exposed by OpenApiLibCore on the target API
it's recommended to first ensure that the openapi document for the API is valid
under the OpenAPI Specification.

This can be done using the command line interface of a package that is installed as
a prerequisite for OpenApiLibCore.
Both a local openapi.json or openapi.yaml file or one hosted by the API server
can be checked using the `prance validate <reference_to_file>` shell command:

```shell
prance validate http://localhost:8000/openapi.json
Processing "http://localhost:8000/openapi.json"...
 -> Resolving external references.
Validates OK as OpenAPI 3.0.2!

prance validate /tests/files/petstore_openapi.yaml
Processing "/tests/files/petstore_openapi.yaml"...
 -> Resolving external references.
Validates OK as OpenAPI 3.0.2!
```

You'll have to change the url or file reference to the location of the openapi
document for your API.

> Note: Although recursion is technically allowed under the OAS, tool support is limited
and changing the API to not use recursion is recommended.
At present OpenApiLibCore has limited support for parsing OpenAPI documents with
recursion in them. See the `recursion_limit` and `recursion_default` parameters.

If the openapi document passes this validation, the next step is trying to do a test
run with a minimal test suite.
The example below can be used, with `source`, `origin` and `path` altered to
fit your situation.

``` robotframework
*** Settings ***
Library            OpenApiLibCore
...                    source=http://localhost:8000/openapi.json
...                    origin=http://localhost:8000

*** Test Cases ***
Getting Started
    ${url}=    Get Valid Url    path=/employees/{employee_id}

```

Running the above suite for the first time may result in an error / failed test.
You should look at the Robot Framework `log.html` to determine the reasons
for the failing tests.
Depending on the reasons for the failures, different solutions are possible.

Details about the OpenApiLibCore library parameters and keywords that you may need can be found
[here](https://marketsquare.github.io/robotframework-openapi-libcore/openapi_libcore.html).

The OpenApiLibCore also support handling of relations between resources within the scope
of the API being validated as well as handling dependencies on resources outside the
scope of the API. In addition there is support for handling restrictions on the values
of parameters and properties.

Details about the `mappings_path` variable usage can be found
[here](https://marketsquare.github.io/robotframework-openapi-libcore/advanced_use.html).

---

## Limitations

There are currently a number of limitations to supported API structures, supported
data types and properties. The following list details the most important ones:
- Only JSON request and response bodies are supported.
- No support for per-endpoint authorization levels.
- Parsing of OAS 3.1 documents is supported by the parsing tools, but runtime behavior is untested.

