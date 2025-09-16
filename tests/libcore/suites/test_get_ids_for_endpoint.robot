*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
...                 default_id_property_name=identification


*** Variables ***
${ORIGIN}       http://localhost:8000


*** Test Cases ***
Test Get Ids From Url That Returns Single Resource
    ${url}=    Get Valid Url    path=/wagegroups/{wagegroup_id}
    ${ids}=    Get Ids From Url    url=${url}
    Length Should Be    item=${ids}    length=1

Test Get Ids From Url That Returns List Of Resources
    # Create an Employee resource so the returned list is not empty
    Get Valid Url    path=/employees/{employee_id}
    ${url}=    Get Valid Url    path=/employees
    ${ids}=    Get Ids From Url    url=${url}
    ${number_of_ids}=    Get Length    item=${ids}
    Should Be True    $number_of_ids > 0

# Test Get Ids From Url That Returns Object Without Id But With Items
