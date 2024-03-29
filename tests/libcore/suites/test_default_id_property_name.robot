*** Settings ***
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
...                 log_suite_variables=${True}
Library         Collections
Variables       ${root}/tests/variables.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Get Valid Id For Endpoint Returns Id For Id Defined In ID_MAPPING
    ${id}=    Get Valid Id For Endpoint    endpoint=/wagegroups    method=post
    Length Should Be    ${id}    36
    Dictionary Should Contain Item    ${OPENAPI_DRIVER_CREATED_DATA}[0]    endpoint    /wagegroups
    Dictionary Should Contain Key    ${OPENAPI_DRIVER_CREATED_DATA}[0]    id

Test Get Valid Id For Endpoint Raises For Resource With Non-default Id
    Run Keyword And Expect Error    Failed to get a valid id using*
    ...    Get Valid Id For Endpoint    endpoint=/available_employees    method=get
