*** Settings ***
Variables           ${ROOT}/tests/variables.py
Library             EtagListener
Library             OpenApiDriver
...                     source=http://localhost:8000/openapi.json
...                     origin=${EMPTY}
...                     base_path=${EMPTY}
...                     mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
...                     response_validation=STRICT
...                     require_body_for_invalid_url=${TRUE}
...                     extra_headers=${API_KEY}
...                     faker_locale=nl_NL
...                     default_id_property_name=identification

Suite Setup         Update Origin
Test Template       Validate Test Endpoint Keyword

Test Tags           rf7


*** Test Cases ***
# robotcode: ignore[ModelError, VariableNotReplaced]
Test Endpoint for ${method} on ${path} where ${status_code} is expected


*** Keywords ***
Validate Test Endpoint Keyword
    [Arguments]    ${path}    ${method}    ${status_code}
    IF    ${status_code} == 404
        Test Invalid Url    path=${path}    method=${method}
    ELSE
        Test Endpoint
        ...    path=${path}    method=${method}    status_code=${status_code}
    END

Update Origin
    Set Origin    http://localhost:8000
