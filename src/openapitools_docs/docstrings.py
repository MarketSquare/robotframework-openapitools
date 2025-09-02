GENERAL_INTRODUCTION = """
My RoboCon 2022 talk about OpenApiDriver and OpenApiLibCore can be found
<a href="https://www.youtube.com/watch?v=7YWZEHxk9Ps" target="_blank">here</a>.

For more information about Robot Framework, see http://robotframework.org.

<hr>

<h2>Installation</h2>

If you already have Python >= 3.10 with pip installed, you can simply run:

<div class="code-block"><pre><code>pip install --upgrade robotframework-openapitools</code></pre></div>

<hr>

<h2>OpenAPI (aka Swagger)</h2>

The OpenAPI Specification (OAS) defines a standard, language-agnostic interface
to RESTful APIs, see https://www.openapis.org/

The OpenApiTools libraries implement a number of Robot Framework keywords that make it
easy to interact with an OpenAPI implementation by using the information in the
OpenAPI document (previously: Swagger file), for examply by automatic generation of
valid values for requests based on the schema information in the document.

<blockquote><i>
Note: The OpenApiTools libraries are designed for APIs based on the OAS v3.
The libraries have not been tested for APIs based on the OAS v2.
</i></blockquote>

<hr>

<h2>Getting started</h2>

Before trying to use the keywords exposed by any of the libraries from OpenApiTools on
the target API, it's recommended to first ensure that the OpenAPI document for the API
is valid under the OpenAPI Specification.

This can be done using the command line interface of the <code>prance</code> package
that is installed as a prerequisite for OpenApiTools.
Both a local openapi.json or openapi.yaml file or one hosted by the API server
can be checked using the <code>prance validate <reference_to_file></code> shell command:

<div class="code-block"><pre><code class="language-bash">
prance validate --backend=openapi-spec-validator http://localhost:8000/openapi.json
Processing "http://localhost:8000/openapi.json"...
 -> Resolving external references.
Validates OK as OpenAPI 3.0.2!

prance validate --backend=openapi-spec-validator /tests/files/petstore_openapi.yaml
Processing "/tests/files/petstore_openapi.yaml"...
 -> Resolving external references.
Validates OK as OpenAPI 3.0.2!

</code></pre></div>

You'll have to change the url or file reference to the location of the openapi
document for your API.

<blockquote><i>
Note: Although recursion is technically allowed under the OAS, tool
support is limited and changing the OAS to not use recursion is recommended.
</i></blockquote>

Support for parsing OpenAPI documents with recursion in them is limited.
See the <code>recursion_limit</code> and <code>recursion_default</code> library
parameters for the available options.

If the OpenAPI document passes this validation, the next step is trying to do a test
run with a minimal test suite.
The examples below can be used with <code>source</code>, <code>origin</code>
and <code>path</code> altered to fit your situation.

<div class="code-block"><pre><code class="language-robotframework">
*** Settings ***
Library            OpenApiDriver
...                    source=http://localhost:8000/openapi.json
...                    origin=http://localhost:8000
Test Template      Validate Using Test Endpoint Keyword

*** Test Cases ***
Test Endpoint for ${method} on ${path} where ${status_code} is expected

*** Keywords ***
Validate Using Test Endpoint Keyword
    [Arguments]    ${path}    ${method}    ${status_code}
    Test Endpoint
    ...    path=${path}    method=${method}    status_code=${status_code}

</code></pre></div>

<div class="code-block"><pre><code class="language-robotframework">
*** Settings ***
Library            OpenApiLibCore
...                    source=http://localhost:8000/openapi.json
...                    origin=http://localhost:8000

*** Test Cases ***
Getting Started
    ${url}=    Get Valid Url    path=/employees/{employee_id}

</code></pre></div>

Running the above tests for the first time may result in an error / failed test.
You should look at the Robot Framework <code>log.html</code> to determine the reasons
for the failing tests.
Depending on the reasons for the failures, different solutions are possible.

The OpenApiTools libraries also support handling of relations between resources within
the scope of the API being validated as well as handling dependencies on resources
outside the scope of the API. In addition there is support for handling restrictions
on the values of parameters and properties.
This is supported by the <code>mappings_path</code> library parameter.
Details about the <code>mappings_path</code> parameter usage can be
found <a href="advanced_use.md" target="_blank">here</a>.

<hr>

<h2>Limitations</h2>

There are currently a number of limitations to supported API structures, supported data
types and properties.
The following list details the most important ones.
- Only JSON request and response bodies are supported.
- No support for per-path authorization levels (only simple 401 / 403 validation).

For all open issues please visit the OpenApiTools <a href="https://github.com/MarketSquare/robotframework-openapitools" target="_blank">GitHub page</a>.
"""

SHARED_PARAMETERS = """
<h2>Base parameters</h2>

<h3>source</h3>
An absolute path to an openapi.json or openapi.yaml file or an url to such a file.

<h3>origin</h3>
The server (and port) of the target server. E.g. <code>https://localhost:8000</code>

<h3>base_path</h3>
The routing between <code>origin</code> and the paths as found in the <code>paths</code>
section in the openapi document.
E.g. <code>/petshop/v2</code>.

<h2>Test case execution</h2>

<h3>response_validation</h3>
By default, a <code>WARN</code> is logged when the Response received after a Request
does not comply with the schema as defined in the OpenAPI document for the given operation.
The following values are supported:
<ul>
<li><code>DISABLED</code>: All Response validation errors will be ignored</li>
<li><code>INFO</code>: Any Response validation erros will be logged at <code>INFO</code> level</li>
<li><code>WARN</code>: Any Response validation erros will be logged at <code>WARN</code> level</li>
<li><code>STRICT</code>: The Test Case will fail on any Response validation errors</li>
</ul>

<h3>disable_server_validation</h3>
If enabled by setting this parameter to <code class="language-robotframework">${TRUE}</code>,
the Response validation will also include possible errors for Requests made to a server
address that is not defined in the list of servers in the OpenAPI document.
This generally means that if there is a mismatch, every Test Case will raise this error.
Note that <code>localhost</code> and <code>127.0.0.1</code> are not considered the same
by Response validation.

<h2>API-specific configurations</h2>

<h3>mappings_path</h3>
See <a href="advanced_use.md" target="_blank">this page</a> for an in-depth explanation.

<h3>invalid_property_default_response</h3>
The default response code for requests with a JSON body that does not comply
with the schema.
Example: a value outside the specified range or a string value
for a property defined as integer in the schema.

<h3>default_id_property_name</h3>
The default name for the property that identifies a resource (i.e. a unique
entity) within the API.
The default value for this property name is <code>id</code>.
If the target API uses a different name for all the resources within the API,
you can configure it globally using this property.

If different property names are used for the unique identifier for different
types of resources, an <code>ID_MAPPING</code> can be implemented using the <code>mappings_path</code>.

<h3>faker_locale</h3>
A locale string or list of locale strings to pass to the Faker library to be
used in generation of string data for supported format types.

<h3>require_body_for_invalid_url</h3>
    When a request is made against an invalid url, this usually is because of a "404" request;
    a request for a resource that does not exist. Depending on API implementation, when a
    request with a missing or invalid request body is made on a non-existent resource,
    either a 404 or a 422 or 400 Response is normally returned. If the API being tested
    processes the request body before checking if the requested resource exists, set
    this parameter to True.

<h2>Parsing parameters</h2>

<h3>recursion_limit</h3>
The recursion depth to which to fully parse recursive references before the
<code>recursion_default</code> is used to end the recursion.

<h3>recursion_default</h3>
The value that is used instead of the referenced schema when the
<code>recursion_limit</code> has been reached.
The default <code class="language-python">{}</code> represents an empty object in JSON.
Depending on schema definitions, this may cause schema validation errors.
If this is the case <code class="language-robotframework">${NONE}</code> or an empty list
can be tried as an alternative.

<h2>Security-related parameters</h2>
<blockquote><i>Note: these parameters are equivalent to those in the <code>requests</code> library.</i></blockquote>

<h3>username</h3>
The username to be used for Basic Authentication.

<h3>password</h3>
The password to be used for Basic Authentication.

<h3>security_token</h3>
The token to be used for token based security using the <code>Authorization</code> header.

<h3>auth</h3>
A <a href="https://requests.readthedocs.io/en/latest/api/#authentication" target="_blank">requests <code>AuthBase</code> instance</a> to be used for authentication instead of the <code>username</code> and <code>password</code>.

<h3>cert</h3>
The SSL certificate to use with all requests.
If string: the path to ssl client cert file (<code>.pem</code>).
If tuple: the <code class="language-python">("cert", "key")</code> pair.

<h3>verify_tls</h3>
Whether or not to verify the TLS / SSL certificate of the server.
If boolean: whether or not to verify the server TLS certificate.
If string: path to a CA bundle to use for verification.

<h3>extra_headers</h3>
A dictionary with extra / custom headers that will be send with every request.
This parameter can be used to send headers that are not documented in the
openapi document or to provide an API-key.

<h3>cookies</h3>
A dictionary or
<a href="https://docs.python.org/3/library/http.cookiejar.html#http.cookiejar.CookieJar" target="_blank"><code>CookieJar</code> object</a>
to send with all requests.

<h3>proxies</h3>
A dictionary of <code>"protocol": "proxy url"</code> to use for all requests.
"""

OPENAPILIBCORE_MODULE_DOCSTRING = """
<h1>OpenApiLibCore for Robot Framework</h1>

The OpenApiLibCore library is a utility library that is meant to simplify creation
of other Robot Framework libraries for API testing based on the information in
an OpenAPI document.
Both OpenApiDriver and libraries generated using OpenApiLibGen rely on OpenApiLibCore
and its keywords for their functionality.
This document explains how to use the OpenApiLibCore library.

<blockquote>
Keyword documentation for OpenApiLibCore can be found <a href="openapi_libcore.html" target="_blank">here</a>.
</blockquote>

<h2>Introduction</h2>
{general_introduction}

""".format(general_introduction=GENERAL_INTRODUCTION)

OPENAPILIBCORE_LIBRARY_DOCSTRING = """
Main class providing the keywords and core logic to interact with an OpenAPI server.

Visit the <a href="documentation.html" target="_blank">OpenApiTools documentation</a> for an introduction.
"""

OPENAPILIBCORE_INIT_DOCSTRING = SHARED_PARAMETERS

OPENAPIDRIVER_MODULE_DOCSTRING = """
<h1>OpenApiDriver for Robot Framework</h1>

OpenApiDriver is an extension of the Robot Framework DataDriver library that allows
for generation and execution of test cases based on the information in an OpenAPI document.

For more information about the DataDriver library, see
https://github.com/Snooz82/robotframework-datadriver.

<blockquote>
Keyword documentation for OpenApiDriver can be found <a href="openapidriver.html" target="_blank">here</a>.
</blockquote>

<h2>Introduction</h2>
{general_introduction}

""".format(general_introduction=GENERAL_INTRODUCTION)

OPENAPIDRIVER_LIBRARY_DOCSTRING = """
Main class providing the keywords and logic for execution of generated test cases based on an OpenAPI document.

Visit the <a href="documentation.html" target="_blank">OpenApiTools documentation</a> for an introduction.
"""

OPENAPIDRIVER_INIT_DOCSTRING = """
<h2>Test case generation and execution</h2>

<h3>included_paths</h3>
A list of paths that will be included when generating the test cases.
The <code>*</code> character can be used at the end of a partial path to include all paths
starting with the partial path (wildcard include).

<h3>ignored_paths</h3>
A list of paths that will be ignored when generating the test cases.
The <code>*</code> character can be used at the end of a partial path to ignore all paths
starting with the partial path (wildcard ignore).

<h3>ignored_responses</h3>
A list of responses that will be ignored when generating the test cases.

<h3>ignored_testcases</h3>
A list of specific test cases that, if it would be generated, will be ignored.
Specific test cases to ignore must be specified as a <code>tuple</code> or
<code>list</code> of <code>path</code>, <code>method</code> and <code>response</code>.

{shared_parameters}
""".format(shared_parameters=SHARED_PARAMETERS)
