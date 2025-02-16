*** Settings ***
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
...                 default_id_property_name=identification
Variables       ${root}/tests/variables.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Get Invalidated Url Raises For Endpoint Not In OpenApi Document
    Run Keyword And Expect Error    ValueError: /dummy not found in paths section of the OpenAPI document.
    ...    Get Invalidated Url    valid_url=${ORIGIN}/dummy

Test Get Invalidated Url Raises For Endpoint That Cannot Be Invalidated
    Run Keyword And Expect Error    ValueError: /employees could not be invalidated.
    ...    Get Invalidated Url    valid_url=${ORIGIN}/employees

Test Get Invalidated Url For Endpoint Ending With Path Id
    ${url}=    Get Valid Url    path=/employees/{employee_id}    method=get
    ${invalidated}=    Get Invalidated Url    valid_url=${url}
    Should Not Be Equal    ${url}    ${invalidated}
    Should Start With    ${invalidated}    http://localhost:8000/employees/

Test Get Invalidated Url For Endpoint Not Ending With Path Id
    ${url}=    Get Valid Url    path=/wagegroups/{wagegroup_id}/employees    method=get
    ${invalidated}=    Get Invalidated Url    valid_url=${url}
    Should Not Be Equal    ${url}    ${invalidated}
    Should Start With    ${invalidated}    http://localhost:8000/wagegroups/
    Should End With    ${invalidated}    /employees

Test Get Invalidated Url For Endpoint With Multiple Path Ids
    ${url}=    Get Valid Url    path=/energy_label/{zipcode}/{home_number}    method=get
    ${invalidated}=    Get Invalidated Url    valid_url=${url}
    Should Not Be Equal    ${url}    ${invalidated}
    Should Start With    ${invalidated}    http://localhost:8000/energy_label/1111AA/

Test Get Invalidated Url For PathPropertiesConstraint Invalid Value Status Code
    ${url}=    Get Valid Url    path=/energy_label/{zipcode}/{home_number}    method=get
    ${invalidated}=    Get Invalidated Url
    ...    valid_url=${url}
    ...    path=/energy_label/{zipcode}/{home_number}
    ...    method=get
    ...    expected_status_code=422
    Should Not Be Equal    ${url}    ${invalidated}
    Should Start With    ${invalidated}    http://localhost:8000/energy_label/0123AA
