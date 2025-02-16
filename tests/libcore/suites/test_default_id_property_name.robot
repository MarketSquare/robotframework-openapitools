*** Settings ***
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
Variables       ${root}/tests/variables.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Get Valid Id For Path Returns Id For Id Defined In ID_MAPPING
    ${id}=    Get Valid Id For Path    path=/wagegroups    method=post
    Length Should Be    ${id}    36

Test Get Valid Id For Path Raises For Resource With Non-default Id
    Run Keyword And Expect Error    Failed to get a valid id using*
    ...    Get Valid Id For Path    path=/available_employees    method=get
