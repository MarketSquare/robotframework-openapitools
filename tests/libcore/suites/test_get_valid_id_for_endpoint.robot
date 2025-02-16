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
Test Get Valid Id For Path Raises For Endpoint Without Id In Path
    Run Keyword And Expect Error    Failed to get a valid id from*
    ...    Get Valid Id For Path    path=/events/    method=get

Test Get Valid Id For Path Raises For Endpoint With No Post Operation And No Resources
    Run Keyword And Expect Error    Failed to get a valid id using GET on*
    ...    Get Valid Id For Path    path=/secret_message    method=get

Test Get Valid Id For Path Returns Id For Resource Created By Post Operation
    ${id}=    Get Valid Id For Path    path=/wagegroups/{wagegroup_id}    method=get
    Length Should Be    ${id}    36

Test Get Valid Id For Path Returns Random Id From Array Endpoint With No Post Operation
    ${url}=    Get Valid Url    path=/employees    method=post
    ${request_data}=    Get Request Data    path=/employees    method=post
    Authorized Request
    ...    url=${url}
    ...    method=post
    ...    json_data=${request_data.get_required_properties_dict()}
    ${id}=    Get Valid Id For Path    path=/available_employees    method=get
    Length Should Be    ${id}    32

# Test Get Valid Id For Path By Href

# Test Get Valid Id For Path Raises For Post Operation That Returns Array
