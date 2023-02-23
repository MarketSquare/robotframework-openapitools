*** Settings ***
Library         OpenApiLibCore
...                 source=${origin}/openapi.json
...                 origin=${origin}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
...                 default_id_property_name=identification
Variables       ${root}/tests/variables.py


*** Variables ***
${origin}=      http://localhost:8000


*** Test Cases ***
Test Get Ids From Url That Returns Single Resource
    ${url}=    Get Valid Url    endpoint=/wagegroups/{wagegroup_id}    method=post
    ${ids}=    Get Ids From Url    url=${url}
    Length Should Be    item=${ids}    length=1

Test Get Ids From Url That Returns List Of Resources
    # Create an Employee resource so the returned list is not empty
    Get Valid Url    endpoint=/employees/{employee_id}    method=get
    ${url}=    Get Valid Url    endpoint=/employees    method=get
    ${ids}=    Get Ids From Url    url=${url}
    ${number_of_ids}=    Get Length    item=${ids}
    Should Be True    $number_of_ids > 0

# Test Get Ids From Url That Returns Object Without Id But With Items
