# OpenApiTools for Robot Framework

OpenApiTools is a set of libraries centered around the OpenAPI Specification:

- [OpenApiDriver](./driver.md)
- [OpenApiLibCore](./libcore.md)


## New in OpenApiTools v1.0.0

Inspired by the work Bartlomiej and Mateusz did on #roboswag, I've created a CLI tool that generates a fully functional Robot Framework (Python) library that builds on OpenApiLibCore for automatic request data generation and request execution.

### So how does it work?
After installing / updating to the v1.0.0 beta (`pip install robotframework-openapitools==1.0.0b3`) , there's a new CLI command available in your (virtual) environment: `generate-library`. You'll have to provide a path to the openapi spec (json or yaml, can be a url or path to the file), provide a path to where to generate the library and (optionally) a name for the library:

```
$ generate-library
Please provide a source for the generation:
$ http://127.0.0.1:8000/openapi.json
Please provide a path to where the library will be generated:
$ ./generated
Please provide a name for the library [default: FastAPI]:
$ My Generated Library
generated/MyGeneratedLibrary/__init__.py created
generated/MyGeneratedLibrary/my_generated_library.py created
```

> Note: there's currently 2 environment variables that are taken into account by the generator; USE_SUMMARY_AS_KEYWORD_NAME can result in nicer keyword names (but: uniqueness is not guaranteed, so you might need to rename some of the generated keywords manually) and EXPAND_BODY_ARGUMENTS is what a recent poll in #api-testing was about.

If the location where the library is located is in your Python search path, you'll be able to use it like a regular Robot Framework library (in fact, it's a drop-in replacement for OpenApiLibCore):

```{robot}
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
```

### Contributions and feedback

So now I need your feedback! Does the library generator work for your openapi spec? Does the library work / do all the generated keywords work? Please let me know of any issues you run into!
Things I'd like to address / improve before an official release:
- parameters with union types (e.g. int or float) are currently annotated as Any.
- support for lists / arrays is limited (i.e. not supported as body)
- objects / dicts are currently only typed as dict; I'm looking into TypedDict annotation for better auto-complete / auto-conversion
- a documentation rework

  Subscribe to https://app.slack.com/client/T07PJQ9S7/CKK0X68KD for updates
