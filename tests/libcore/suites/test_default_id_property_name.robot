*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py


*** Variables ***
${ORIGIN}       http://localhost:8000


*** Test Cases ***
Test Get Valid Id For Path Returns Id For Id Defined In ID_MAPPING
    ${id}=    Get Valid Id For Path    path=/wagegroups
    Length Should Be    ${id}    36

Test Get Valid Id For Path Raises For Resource With Non-default Id
    Run Keyword And Expect Error    Failed to get a valid id using*
    ...    Get Valid Id For Path    path=/available_employees
