*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
...                 default_id_property_name=identification


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Get Parameterized Path From Url Raises For Invalid Endpoint
    Run KeyWord And Expect Error    ValueError: /dummy not found in paths section of the OpenAPI document.
    ...    Get Parameterized Path From Url    url=${ORIGIN}/dummy

Test Get Parameterized Path From Url With No Id
    ${url}=    Get Valid Url    path=/events/
    ${endpoint}=    Get Parameterized Path From Url    url=${url}
    Should Be Equal    ${endpoint}    /events/

Test Get Parameterized Path From Url With Single Id
    ${url}=    Get Valid Url    path=/employees/{employee_id}
    ${endpoint}=    Get Parameterized Path From Url    url=${url}
    Should Be Equal    ${endpoint}    /employees/{employee_id}

# Test Get Parameterized Path From Url With Multiple Ids
#    ${url}=    Get Valid Url    path=/events/
#    Get Parameterized Path From Url    url=${url}
