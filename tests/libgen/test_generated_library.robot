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
Test Generated Keyword: Get Employees
    ${response}=    Get Employees
    Should Be Equal As Integers    ${response.status_code}    200

Test Generated Keyword: Post Employee
    ${response}=    Post Employee
    Should Be Equal As Integers    ${response.status_code}    201
