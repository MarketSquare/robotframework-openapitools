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
Test Get Valid Url Raises For Invalid Endpoint
    Run Keyword And Expect Error    ValueError: /dummy not found in paths section of the OpenAPI document.
    ...    Get Valid Url    endpoint=/dummy    method=get

Test Get Valid Url With Unsupported Method
    ${url}=    Get Valid Url    endpoint=/events/    method=patch
    Should Be Equal    ${url}    ${origin}/events/

Test Get Valid Url With Id
    ${url}=    Get Valid Url    endpoint=/wagegroups/{wagegroup_id}    method=get
    Should Contain    container=${url}    item=${origin}/wagegroups/

Test Get Valid Url By PathPropertiesContraint
    ${url}=    Get Valid Url    endpoint=/energy_label/{zipcode}/{home_number}    method=get
    Should Be Equal As Strings    ${url}    ${origin}/energy_label/1111AA/10
