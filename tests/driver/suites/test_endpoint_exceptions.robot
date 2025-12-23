*** Settings ***
Variables           ${ROOT}/tests/variables.py
Library             OpenApiDriver
...                     source=http://localhost:8000/openapi.json
...                     origin=http://localhost:8000
...                     included_paths=${INCLUDED_PATHS}
...                     invalid_data_default_response=400

Test Template       Validate Test Endpoint Keyword


*** Variables ***
@{INCLUDED_PATHS}       /secret_message


*** Test Cases ***
# robotcode: ignore[ModelError, VariableNotReplaced]
Test Endpoint for ${method} on ${path} where ${status_code} is expected


*** Keywords ***
Validate Test Endpoint Keyword
    [Arguments]    ${path}    ${method}    ${status_code}
    IF    $status_code == "200"
        Run Keyword And Expect Error    Response status_code 401 was not 200.
        ...    Test Endpoint    path=${path}    method=${method}    status_code=${status_code}
    ELSE
        Run Keyword And Expect Error    No relation found to cause status_code ${status_code}.
        ...    Test Endpoint    path=${path}    method=${method}    status_code=${status_code}
    END
