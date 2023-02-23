*** Settings ***
Library         OpenApiLibCore
...                 source=${origin}/openapi.json
...                 origin=${origin}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
Variables       ${root}/tests/variables.py


*** Variables ***
${origin}=      http://localhost:8000


*** Test Cases ***
Test Get Valid Id For Endpoint Returns Id For Id Defined In ID_MAPPING
    ${id}=    Get Valid Id For Endpoint    endpoint=/wagegroups    method=post
    Length Should Be    ${id}    36

Test Get Valid Id For Endpoint Raises For Resource With Non-default Id
    Run Keyword And Expect Error    Failed to get a valid id using*
    ...    Get Valid Id For Endpoint    endpoint=/available_employees    method=get
