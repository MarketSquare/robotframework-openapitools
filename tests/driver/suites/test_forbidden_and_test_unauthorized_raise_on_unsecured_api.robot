*** Settings ***
Variables           ${ROOT}/tests/variables.py
Library             OpenApiDriver
...                     source=http://localhost:8000/openapi.json
...                     origin=http://localhost:8000
...                     base_path=${EMPTY}
...                     ignored_responses=${IGNORED_RESPONSES}
...                     mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
...                     extra_headers=${API_KEY}

Test Template       Validate Unsecured Requests


*** Variables ***
@{IGNORED_RESPONSES}    401    403    404    406    412    418    422    451


*** Test Cases ***
# robotcode: ignore[ModelError, VariableNotReplaced]
Test unsecured requests for ${method} on ${path}


*** Keywords ***
Validate Unsecured Requests
    [Arguments]    ${path}    ${method}
    Run Keyword And Expect Error    Response ??? was not 401.
    ...    Test Unauthorized    path=${path}    method=${method}

    Run Keyword And Expect Error    Response ??? was not 403.
    ...    Test Forbidden    path=${path}    method=${method}
