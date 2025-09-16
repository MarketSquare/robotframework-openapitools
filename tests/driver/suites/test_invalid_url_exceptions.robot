*** Settings ***
Variables           ${ROOT}/tests/variables.py
Library             OpenApiDriver
...                     source=http://localhost:8000/openapi.json
...                     origin=http://localhost:8000
...                     included_paths=${INCLUDED_PATHS}
...                     mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
...                     require_body_for_invalid_url=${FALSE}

Test Template       Validate Test Invalid Url Skips Or Raises


*** Variables ***
@{INCLUDED_PATHS}       /events/    /energy_label/{zipcode}/{home_number}


*** Test Cases ***
# robotcode: ignore[ModelError, VariableNotReplaced]
Test Endpoint for ${method} on ${path} where ${status_code} is expected


*** Keywords ***
Validate Test Invalid Url Skips Or Raises
    [Arguments]    ${path}    ${method}    ${status_code}
    # The expected status code can never occur, so it will fail unless skipped (which is what is expected)
    Run Keyword And Expect Error    Response 422 was not 9999
    ...    Test Invalid Url    path=${path}    method=${method}    expected_status_code=9999
