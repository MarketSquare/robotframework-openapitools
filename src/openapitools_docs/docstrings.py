GENERAL_INTRODUCTION = """
My RoboCon 2022 talk about OpenApiDriver and OpenApiLibCore can be found
<a href="https://www.youtube.com/watch?v=7YWZEHxk9Ps" target="_blank">here</a>.

For more information about Robot Framework, see http://robotframework.org.

<hr>

<h2>Installation</h2>

If you already have Python >= 3.10 with pip installed, you can simply run:

<div class="code-block"><pre><code class="language-shell">pip install --upgrade robotframework-openapitools</code></pre></div>

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

<div class="code-block"><pre><code class="language-shell">
(.venv) prance validate --backend=openapi-spec-validator http://localhost:8000/openapi.json

Processing "http://localhost:8000/openapi.json"...
 -> Resolving external references.
Validates OK as OpenAPI 3.0.2!

(.venv) prance validate --backend=openapi-spec-validator /tests/files/petstore_openapi.yaml

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
found under the Advanced Use tab.

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
See the Advanced Use tab for an in-depth explanation.

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

OPENAPILIBCORE_DOCUMENTATION = """
<h1>OpenApiLibCore for Robot Framework</h1>

The OpenApiLibCore library is a utility library that is meant to simplify creation
of other Robot Framework libraries for API testing based on the information in
an OpenAPI document.
Both OpenApiDriver and libraries generated using OpenApiLibGen rely on OpenApiLibCore
and its keywords for their functionality.
This document explains how to use the OpenApiLibCore library.

<blockquote>
Keyword documentation for OpenApiLibCore can be found <a href="./openapi_libcore.html" target="_blank">here</a>.
</blockquote>

<h2>Introduction</h2>
{general_introduction}

""".format(general_introduction=GENERAL_INTRODUCTION)

OPENAPILIBCORE_LIBRARY_DOCSTRING = """
The OpenApiLibCore library provides the keywords and core logic to interact with an OpenAPI server.

Visit the <a href="./index.html" target="_blank">OpenApiTools documentation</a> for an introduction.
"""

OPENAPILIBCORE_INIT_DOCSTRING = SHARED_PARAMETERS

OPENAPIDRIVER_DOCUMENTATION = """
<h1>OpenApiDriver for Robot Framework</h1>

OpenApiDriver is an extension of the Robot Framework DataDriver library that allows
for generation and execution of test cases based on the information in an OpenAPI document.

For more information about the DataDriver library, see
https://github.com/Snooz82/robotframework-datadriver.

<blockquote>
Keyword documentation for OpenApiDriver can be found <a href="./openapidriver.html" target="_blank">here</a>.
</blockquote>

<h2>Introduction</h2>
{general_introduction}

""".format(general_introduction=GENERAL_INTRODUCTION)

OPENAPIDRIVER_LIBRARY_DOCSTRING = """
The OpenApiDriver library provides the keywords and logic for execution of generated test cases based on an OpenAPI document.

Visit the <a href="./index.html" target="_blank">OpenApiTools documentation</a> for an introduction.
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

OPENAPILIBGEN_DOCUMENTATION = """
<h1>OpenApiLibGen for Robot Framework</h1>

OpenApiLibGen is a command-line tool that can be used to generate a Robot Framework
library based on an OpenAPI document.

<hr>

In a (virtual) environment where <code>robotframework-openapitools</code> is installed
the <code>generate-library</code> shell command is availabe:

<div class="code-block"><pre><code class="language-shell">
$ generate-library -h
usage: openapi_libgen [-h] [-s SOURCE] [-d DESTINATION] [-n NAME] [--recursion-limit RECURSION_LIMIT]
                      [--recursion-default RECURSION_DEFAULT]

The OpenApiTools library generator

options:
  -h, --help            show this help message and exit
  -s SOURCE, --source SOURCE
  -d DESTINATION, --destination DESTINATION
  -n NAME, --name NAME
  --recursion-limit RECURSION_LIMIT
  --recursion-default RECURSION_DEFAULT

Inspired by roboswag. Thank you Bartlomiej and Mateusz for your work!
</code></pre></div>

Generation of your library is an interactive process with a few steps:

<div class="code-block"><pre><code class="language-shell">
$ generate-library
Please provide a source for the generation:
$ http://127.0.0.1:8000/openapi.json
Please provide a path to where the library will be generated:
$ ./generated
Please provide a name for the library [default: FastAPI]:
$ My Generated Library
generated/MyGeneratedLibrary/__init__.py created
generated/MyGeneratedLibrary/my_generated_library.py created
</code></pre></div>

<div><codeblock>
Tip: The name for the  library that you provide (or that's taken from the OpenAPI document)
will be transformed into a Python-legal module name and a Python-legal class name.
This means special characters like <code>-</code> will be removed or replaced.
If you used spaces in the desired name, they will be removed from the Library (class) name
and the next character will be capitalized while the spaces will be replaced with an
underscore in the module name as can be seen in the example above.
</codeblock></div>

<div><pre><codeblock><i>
Note: There's currently 2 environment variables that are taken into account by the generator:
    <code>USE_SUMMARY_AS_KEYWORD_NAME</code> can result in nicer keyword names (but: uniqueness is not guaranteed, so you might need to rename some of the generated keywords manually)
    <code>EXPAND_BODY_ARGUMENTS</code> changes how body arguments are provided to keywords (either a single body dict or key-value pairs for the body parameters)
</i><pre></codeblock></div>

<hr>

If the location where the library is located is in your Python search path, you'll be able
to use it like a regular Robot Framework library (in fact, it's a drop-in replacement for
OpenApiLibCore).

The generated library has a keyword for every endpoint in the OpenAPI document used to generated it.
In addition, all the keywords from OpenApiLibCore are available.
<blockquote>
Keyword documentation for OpenApiLibCore can be found <a href="./openapi_libcore.html" target="_blank">here</a>.
</blockquote>

The generated library can be used as shown below:

<div class="code-block"><pre><code class="language-robotframework">
*** Settings ***
Library         MyGeneratedLibrary
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
Variables       ${ROOT}/tests/variables.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Generated Keywords: Get Employees
    ${response}=    Get Employees
    Should Be Equal As Integers    ${response.status_code}    200

Test Generated Keywords: Post Employee
    VAR    &{body}    name=Robin the Robot
    ${response}=    Post Employee    body=${body}
    # ${response}=    Post Employee    name=Robin the Robot
    Should Be Equal As Integers    ${response.status_code}    201
    Should Be Equal    ${response.json()}[name]    Robin the Robot

Test Generated Keywords: Get Employee
    ${response}=    Get Employee
    Should Be Equal As Integers    ${response.status_code}    200

Test Generated Keywords: Patch Employee
    ${employee_id}=    Get Valid Id For Path    path=/employees/{employee_id}
    VAR    &{body}    date_of_birth=2021-12-31
    ${response}=    Patch Employee    employee_id=${employee_id}    body=${body}
    # ${response}=    Patch Employee    employee_id=${employee_id}    date_of_birth=2021-12-31
    Should Be Equal As Integers    ${response.status_code}    403

Test Generated Keywords: Post WageGroup
    VAR    &{body}    hourly_rate=99.99
    ${response}=    Post Wagegroup    body=${body}
    # ${response}=    Post Wagegroup    hourly_rate=99.99
    Should Be Equal As Integers    ${response.status_code}    201
    Should Be Equal As Numbers    ${response.json()}[hourly-rate]    99.99

Test Generated Keywords: Get Energy Label
    ${response}=    Get Energy Label
    ...    zipcode=1111AA
    ...    home_number=10
    ...    extension=too long to be acceptable
    ...    validate_against_schema=${FALSE}
    Should Be Equal As Integers    ${response.status_code}    422

    VAR    @{omit}    extension
    ${response}=    Get Energy Label
    ...    zipcode=1111AA
    ...    home_number=10
    ...    extension=too long to be acceptable
    ...    omit_parameters=${omit}
    Should Be Equal As Integers    ${response.status_code}    200
</code></pre></div>
"""

ADVANCED_USE_DOCUMENTATION = """
<h1>Advanced use scenario's: using the mappings_path</h1>

<h2>Introduction</h2>
When working with APIs, there are often relations between resources or constraints on values.
The property on one resource may refer to the <code>id</code> of another resource.
The value for a certain property may have to be unique within a certain scope.
Perhaps an url contains parameters that must match values that are defined outside the API itself.

These types of relations and limitations cannot be described / modeled within the openapi document.
To support automatic validation of API endpoints where such relations apply, OpenApiLibCore supports the usage of a custom mappings file.

<h2>Taking a custom mappings file into use</h2>
To take a custom mappings file into use, the absolute path to it has to be passed to OpenApiLibCore as the <code>mappings_path</code> parameter:

<div class="code-block"><pre><code class="language-robotframework">
*** Settings ***
Library             OpenApiLibCore
...                     source=http://localhost:8000/openapi.json
...                     origin=http://localhost:8000
...                     mappings_path=${ROOT}/tests/custom_user_mappings.py
...

</code></pre></div>

<blockquote><i>
Note: An absolute path is required.
In the example above, <code>${ROOT}</code> is a global variable that holds the absolute path to the repository root.
</i></blockquote>

<h2>The custom mappings file</h2>
Just like custom Robot Framework libraries, the mappings file has to be implemented in Python.
Since this Python file is imported by the OpenApiLibCore, it has to follow a fixed format (more technically, implement a certain interface).
The (almost) bare minimum implementation of a mappings.py file looks like this:

<div class="code-block"><pre><code class="language-python">
from OpenApiLibCore import (
    IGNORE,
    Dto,
    IdDependency,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    UniquePropertyValueConstraint,
)


ID_MAPPING = {
    "/myspecialpath", "special_thing_id",
}


class MyDtoThatDoesNothing(Dto):
    @staticmethod
    def get_relations():
        relations = []
        return relations

    @staticmethod
    def get_path_relations():
        relations = []
        return relations

    @staticmethod
    def get_parameter_relations():
        relations = []
        return relations


DTO_MAPPING = {
    ("/myspecialpath", "post"): MyDtoThatDoesNothing
}


PATH_MAPPING = {
    "/mypathwithexternalid/{external_id}": MyDtoThatDoesNothing
}

</code></pre></div>

There are 5 main parts in this mappings file:

<ol type="1">
<li>The import section.
Here the classes needed to implement custom mappings are imported.
This section can just be copied without changes.</li>
<li>The <code class="language-python">ID_MAPPING</code> "constant" definition / assignment.</li>
<li>The section defining the mapping Dtos. More on this later.</li>
<li>The <code class="language-python">DTO_MAPPING</code> "constant" definition / assignment.</li>
<li>The <code class="language-python">PATH_MAPPING</code> "constant" definition / assignment.</li>
</ol>

<h2>The ID_MAPPING, DTO_MAPPING and PATH_MAPPING</h2>
When a custom mappings file is used, the OpenApiLibCore will attempt to import it and then import <code>DTO_MAPPING</code>, <code>PATH_MAPPING</code> and <code>ID_MAPPING</code> from it.
For this reason, the exact same name must be used in a custom mappings file (capitilization matters).

<h3>The ID_MAPPING</h3>
The <code>ID_MAPPING</code> is a dictionary with a string as its key and either a string or a tuple of string and a callable as its value. The callable must take a string as its argument and return a string.

The <code>ID_MAPPING</code> is used to specify what the unique identifier property of a resource at the given path is, if different from the <code>default_id_property_name</code> (see library parameters).

In some situations, the identifier of the resource is not url-safe (e.g. containing a <code class="language-python">/</code>).
To support this type of resource identifier, a transformer can be provided:

<div class="code-block"><pre><code class="language-python">
def my_transformer(identifier_name: str) -> str:
    return identifier_name.replace("/", "_")


ID_MAPPING = {
    "/myspecialpath": ("special_thing_id", my_transformer),
}

</code></pre></div>

<h3>The DTO_MAPPING</h3>
The <code>DTO_MAPPING</code> is a dictionary with a tuple as its key and a mappings Dto as its value.
The tuple must be in the form <code class="language-python">("path_from_the_paths_section", "method_supported_by_the_path")</code>.
The <code class="language-python">path_from_the_paths_section</code> must be exactly as found in the openapi document.
The <code class="language-python">method_supported_by_the_path</code> must be one of the methods supported by the path and must be in lowercase.

<h3>The PATH_MAPPING</h3>
The <code>PATH_MAPPING</code> is a dictionary with a <code>"path_from_the_paths_section"</code> as its key and a mappings Dto as its value.
The <code>path_from_the_paths_section</code> must be exactly as found in the openapi document.


<h2>Dto mapping classes</h2>
As can be seen from the import section above, a number of classes are available to deal with relations between resources and / or constraints on properties.
Each of these classes is designed to handle a relation or constraint commonly seen in REST APIs.

To explain the different mapping classes, we'll use the following example:

<blockquote>
Imagine we have an API path <code>/employees</code> where we can create (<code>post</code>) a new Employee resource.
The Employee has a number of required properties; name, employee_number, wagegroup_id, and date_of_birth.

There is also the the <code>/wagegroups</code> path where a Wagegroup resource can be created.
This Wagegroup also has a number of required properties: <code>name</code> and <code>hourly rate</code>.
</blockquote>

<hr>

<h3><code>IdReference</code></h3>
<blockquote><u>The value for this propery must the the <code>id</code> of another resource</u></blockquote>

To add an Employee, a <code>wagegroup_id</code> is required, the <code>id</code> of a Wagegroup resource that is already present in the system.

Since a typical REST API generates this <code>id</code> for a new resource and returns that <code>id</code> as part of the <code>post</code> response, the required <code>wagegroup_id</code> can be obtained by posting a new Wagegroup.
This relation can be implemented as follows:

<div class="code-block"><pre><code class="language-python">
class EmployeeDto(Dto):
    @staticmethod
    def get_relations():
        relations = [
            IdDependency(
                property_name="wagegroup_id",
                get_path="/wagegroups",
                error_code=451,
            ),
        ]
        return relations

DTO_MAPPING = {
    ("/employees", "post"): EmployeeDto
}

</code></pre></div>

Notice that the <code>get_path</code> of the <code>IdDependency</code> is not named <code>post_path</code> as one might expect.
This is deliberate for two reasons:

1. The purpose is getting an <code>id</code>
2. If the <code>post</code> operation is not supported on the provided path, a <code>get</code> operation is performed instead.
It is assumed that such a <code>get</code> will yield a list of resources and that each of these resources has an <code>id</code> that is valid for the desired <code>post</code> operation.

Also note the <code>error_code</code> of the <code>IdDependency</code>.
If a <code>post</code> is attempted with a value for the <code>wagegroup_id</code> that does not exist, the API should return an <code>error_code</code> response.
This <code>error_code</code> should be described as one of the <code>responses</code> in the openapi document for the <code>post</code> operation of the <code>/employees</code> path.

<hr>

<h3><code>IdDependency</code></h3>
<blockquote><u>This resource may not be DELETED if another resource refers to it</u></blockquote>

If an Employee has been added to the system, this Employee refers to the <code>id</code> of a Wagegroup for its required <code>employee_number</code> property.

Now let's say there is also the <code>/wagegroups/${wagegroup_id}</code> path that supports the <code>delete</code> operation.
If the Wagegroup refered to the Employee would be deleted, the Employee would be left with an invalid reference for one of its required properties.
To prevent this, an API typically returns an <code>error_code</code> when such a <code>delete</code> operation is attempted on a resource that is refered to in this fashion.
This <code>error_code</code> should be described as one of the <code>responses</code> in the openapi document for the <code>delete</code> operation of the <code>/wagegroups/${wagegroup_id}</code> path.

To verify that the specified <code>error_code</code> indeed occurs when attempting to <code>delete</code> the Wagegroup, we can implement the following dependency:

<div class="code-block"><pre><code class="language-python">
class WagegroupDto(Dto):
    @staticmethod
    def get_relations():
        relations = [
            IdReference(
                property_name="wagegroup_id",
                post_path="/employees",
                error_code=406,
            ),
        ]
        return relations

DTO_MAPPING = {
    ("/wagegroups/{wagegroup_id}", "delete"): WagegroupDto
}

</code></pre></div>

<hr>

<h3><code>UniquePropertyValueConstraint</code></h3>
<blockquote><u>The value of this property must be unique within its scope</u></blockquote>

In a lot of systems, there is data that should be unique; an employee number, the email address of an employee, the domain name for the employee, etc.
Often those values are automatically generated based on other data, but for some data, an "available value" must be chosen by hand.

In our example, the required <code>employee_number</code> must be chosen from the "free" numbers.
When a number is chosen that is already in use, the API should return the <code>error_code</code> specified in the openapi document for the operation (typically <code>post</code>, <code>put</code> and <code>patch</code>) on the endpoint.

To verify that the specified <code>error_code</code> occurs when attempting to <code>post</code> an Employee with an <code>employee_number</code> that is already in use, we can implement the following dependency:

<div class="code-block"><pre><code class="language-python">
class EmployeeDto(Dto):
    @staticmethod
    def get_relations():
        relations = [
            UniquePropertyValueConstraint(
                property_name="employee_number",
                value=42,
                error_code=422,
            ),
        ]
        return relations

DTO_MAPPING = {
    ("/employees", "post"): EmployeeDto,
    ("/employees/${employee_id}", "put"): EmployeeDto,
    ("/employees/${employee_id}", "patch"): EmployeeDto,
}

</code></pre></div>

Note how this example reuses the <code>EmployeeDto</code> to model the uniqueness constraint for all the operations (<code>post</code>, <code>put</code> and <code>patch</code>) that all relate to the same <code>employee_number</code>.

<hr>

<h3><code>PropertyValueConstraint</code></h3>
<blockquote><u>Use one of these values for this property</u></blockquote>

The OpenApiLibCore uses the <code>type</code> information in the openapi document to generate random data of the correct type to perform the operations that need it.
While this works in many situations (e.g. a random <code>string</code> for a <code>name</code>), there can be additional restrictions to a value that cannot be specified in an openapi document.

In our example, the <code>date_of_birth</code> must be a string in a specific format, e.g. 1995-03-27.
This type of constraint can be modeled as follows:

<div class="code-block"><pre><code class="language-python">
class EmployeeDto(Dto):
    @staticmethod
    def get_relations():
        relations = [
            PropertyValueConstraint(
                property_name="date_of_birth",
                values=["1995-03-27", "1980-10-02"],
                error_code=422,
            ),
        ]
        return relations

DTO_MAPPING = {
    ("/employees", "post"): EmployeeDto,
    ("/employees/${employee_id}", "put"): EmployeeDto,
    ("/employees/${employee_id}", "patch"): EmployeeDto,
}

</code></pre></div>

Now in addition, there could also be the restriction that the Employee must be 18 years or older.
To support additional restrictions like these, the <code class="language-python">PropertyValueConstraint</code> supports two additional properties: <code class="language-python">error_value</code> and <code class="language-python">invalid_value_error_code</code>:

<div class="code-block"><pre><code class="language-python">
class EmployeeDto(Dto):
    @staticmethod
    def get_relations():
        relations = [
            PropertyValueConstraint(
                property_name="date_of_birth",
                values=["1995-03-27", "1980-10-02"],
                error_code=422,
                invalid_value="2020-02-20",
                invalid_value_error_code=403,
            ),
        ]
        return relations

DTO_MAPPING = {
    ("/employees", "post"): EmployeeDto,
    ("/employees/${employee_id}", "put"): EmployeeDto,
    ("/employees/${employee_id}", "patch"): EmployeeDto,
}

</code></pre></div>

So now if an incorrectly formatted date is send a 422 response is expected, but when <code>2020-02-20</code> is send the expected repsonse is 403.

In some API implementations, there may be a property that will always return a specific error code if it's value is not valid.
This means that sending e.g. an invalid type of value will not result in the default error code for the API (typically 422 or 400).
This situation can be handled by use of the special <code class="language-python">IGNORE</code> value (see below for other uses):

<div class="code-block"><pre><code class="language-python">
class EmployeeDto(Dto):
    @staticmethod
    def get_relations():
        relations = [
            PropertyValueConstraint(
                property_name="date_of_birth",
                values=["1995-03-27", "1980-10-02"],
                error_code=403,
                invalid_value=IGNORE,
                invalid_value_error_code=422,
            ),
        ]
        return relations

DTO_MAPPING = {
    ("/employees", "post"): EmployeeDto,
    ("/employees/${employee_id}", "put"): EmployeeDto,
    ("/employees/${employee_id}", "patch"): EmployeeDto,
}

</code></pre></div>

Note that while this configuration will prevent failing test cases generated by OpenApiDriver, it does not explicitly check for business logic errors anymore (younger than 18 in this example).

<hr>

<h3><code>PathPropertiesConstraint</code></h3>
<blockquote><u>Just use this for the <code>path</code></u></blockquote>

<blockquote><i>
Note: The <code class="language-python">PathPropertiesConstraint</code> is only applicable to the <code class="language-python">get_path_relations</code> in a <code class="language-python">Dto</code> and only the <code class="language-python">PATH_MAPPING</code> uses the <code class="language-python">get_path_relations</code>.
</i></blockquote>

To be able to automatically perform endpoint validations, the OpenApiLibCore has to construct the <code>url</code> for the resource from the <code>path</code> as found in the openapi document.
Often, such a <code>path</code> contains a reference to a resource id, e.g. <code class="language-python">"/employees/${employee_id}"</code>.
When such an <code>id</code> is needed, the OpenApiLibCore tries to obtain a valid <code>id</code> by taking these steps:

1. Attempt a <code>post</code> on the "parent path" and extract the <code>id</code> from the response.
In our example: perform a <code>post</code> request on the <code>/employees</code> path and get the <code>id</code> from the response.
2. If 1. fails, perform a <code>get</code> request on the <code>/employees</code> path. It is assumed that this will return a list of Employee objects with an <code>id</code>.
One item from the returned list is picked at rondom and its <code>id</code> is used.

This mechanism relies on the standard REST structure and patterns.

Unfortunately, this structure / pattern does not apply to every endpoint; not every path parameter refers to a resource id.
Imagine we want to extend the API from our example with an endpoint that returns all the Employees that have their birthday at a given date:
<code class="language-python">"/birthdays/${month}/${date}"</code>.
It should be clear that the OpenApiLibCore won't be able to acquire a valid <code>month</code> and <code>date</code>. The <code class="language-python">PathPropertiesConstraint</code> can be used in this case:

<div class="code-block"><pre><code class="language-python">
class BirthdaysDto(Dto):
    @staticmethod
    def get_path_relations():
        relations = [
            PathPropertiesConstraint(path="/birthdays/03/27"),
        ]
        return relations

PATH_MAPPING = {
    "/birthdays/{month}/{date}": BirthdaysDto
}

</code></pre></div>

<hr>

<h3><code>IGNORE</code></h3>
<blockquote><u>Never send this query parameter as part of a request</u></blockquote>

Some optional query parameters have a range of valid values that depend on one or more path parameters.
Since path parameters are part of an url, they cannot be optional or empty so to extend the path parameters with optional parameters, query parameters can be used.

To illustrate this, let's imagine an API where the energy label for a building can be requested: <code class="language-python">"/energylabel/${zipcode}/${home_number}"</code>.
Some addresses however have an address extension, e.g. 1234AB 42 <sup>2.C</sup>.
The extension may not be limited to a fixed pattern / range and if an address has an extension, in many cases the address without an extension part is invalid.

To prevent OpenApiLibCore from generating invalid combinations of path and query parameters in this type of endpoint, the <code class="language-python">IGNORE</code> special value can be used to ensure the related query parameter is never send in a request.

<div class="code-block"><pre><code class="language-python">
class EnergyLabelDto(Dto):
    @staticmethod
    def get_parameter_relations():
        relations = [
            PropertyValueConstraint(
                property_name="address_extension",
                values=[IGNORE],
                error_code=422,
            ),
        ]
        return relations

    @staticmethod
    def get_relations(:
        relations = [
            PathPropertiesConstraint(path="/energy_label/1111AA/10"),
        ]
        return relations

DTO_MAPPING = {
    ("/energy_label/{zipcode}/{home_number}", "get"): EnergyLabelDto
}

</code></pre></div>

Note that in this example, the <code class="language-python">get_parameter_relations()</code> method is implemented.
This method works mostly the same as the <code class="language-python">get_relations()</code> method but applies to headers and query parameters.

<hr>

<h2>Type annotations</h2>

An additional import to support type annotations is also available: <code class="language-python">Relation</code>.
A fully typed example can be found
<a href="https://github.com/MarketSquare/robotframework-openapitools/blob/main/tests/user_implemented/custom_user_mappings.py" target="_blank">here</a>.
"""