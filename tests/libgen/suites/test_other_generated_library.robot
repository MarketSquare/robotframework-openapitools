*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         MyOtherGeneratedLibrary
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py

Test Tags       rf7


*** Variables ***
${ORIGIN}       http://localhost:8000


*** Test Cases ***
Test Generated Keywords: Get Employees
    ${response}=    Get Employees
    Should Be Equal As Integers    ${response.status_code}    200

Test Generated Keywords: Post Employee
    ${response}=    Post Employee    name=Robin the Robot
    Should Be Equal As Integers    ${response.status_code}    201
    Should Be Equal    ${response.json()}[name]    Robin the Robot

Test Generated Keywords: Get Employee
    ${response}=    Get Employee
    Should Be Equal As Integers    ${response.status_code}    200

Test Generated Keywords: Patch Employee
    ${employee_id}=    Get Valid Id For Path    path=/employees/{employee_id}
    ${response}=    Patch Employee    employee_id=${employee_id}    date_of_birth=2021-12-31
    Should Be Equal As Integers    ${response.status_code}    403

Test Generated Keywords: Post WageGroup
    ${response}=    Post Wagegroup    hourly_rate=99.99
    Should Be Equal As Integers    ${response.status_code}    201
    Should Be Equal As Numbers    ${response.json()}[hourly-rate]    99.99

Test Generated Keywords: Get Energy Label
    ${response}=    Get Energy Label
    ...    zipcode=1111AA
    ...    home_number=10
    ...    extension=too long to be acceptable
    ...    validate_against_schema=${FALSE}
    Should Be Equal As Integers    ${response.status_code}    422

    VAR    @{omit}=    extension
    ${response}=    Get Energy Label
    ...    zipcode=1111AA
    ...    home_number=10
    ...    extension=too long to be acceptable
    ...    omit_parameters=${omit}
    Should Be Equal As Integers    ${response.status_code}    200
