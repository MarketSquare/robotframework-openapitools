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
    ${response}=    Post Employee    name=Robin the Robot
    Should Be Equal As Integers    ${response.status_code}    201
    Should Be Equal    ${response.json()}[name]    Robin the Robot

Test Generated Keyword: Get Employee
    ${response}=    Get Employee
    Should Be Equal As Integers    ${response.status_code}    200

Test Generated Keyword: Patch Employee
    ${employee_id}=    Get Valid Id For Path    path=/employees/{employee_id}
    ${response}=    Patch Employee    employee_id=${employee_id}    date_of_birth=2021-12-31
    Should Be Equal As Integers    ${response.status_code}    403
