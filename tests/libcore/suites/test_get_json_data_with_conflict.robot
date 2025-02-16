*** Settings ***
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
Variables       ${root}/tests/variables.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Get Json Data With Conflict Raises For No UniquePropertyValueConstraint
    ${url}=    Get Valid Url    path=/wagegroups    method=post
    Run Keyword And Expect Error    ValueError: No UniquePropertyValueConstraint*
    ...    Get Json Data With Conflict
    ...    url=${url}
    ...    method=post
    ...    dto=${DEFAULT_DTO()}
    ...    conflict_status_code=418

Test Get Json Data With Conflict For Post Request
    ${url}=    Get Valid Url    path=/wagegroups    method=post
    ${request_data}=    Get Request Data    path=/wagegroups    method=post
    ${invalid_data}=    Get Json Data With Conflict
    ...    url=${url}
    ...    method=post
    ...    dto=${request_data.dto}
    ...    conflict_status_code=418
    Should Not Be Empty    ${invalid_data}

Test Get Json Data With Conflict For Put Request
    ${url}=    Get Valid Url    path=/wagegroups/{wagegroup_id}    method=put
    ${request_data}=    Get Request Data    path=/wagegroups/{wagegroup_id}    method=put
    ${invalid_json}=    Get Json Data With Conflict
    ...    url=${url}
    ...    method=put
    ...    dto=${request_data.dto}
    ...    conflict_status_code=418
    ${response}=    Authorized Request
    ...    url=${url}    method=put    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    418

# Test Get Json Data With Conflict For Patch Request
#    ${url}=    Get Valid Url    path=/wagegroups/{wagegroup_id}    method=put
#    ${request_data}=    Get Request Data    path=/wagegroups/{wagegroup_id}    method=put
#    ${invalid_json}=    Get Json Data With Conflict
#    ...    url=${url}
#    ...    method=put
#    ...    dto=${request_data.dto}
#    ...    conflict_status_code=418
#    ${response}=    Authorized Request
#    ...    url=${url}    method=put    json_data=${invalid_json}
#    Should Be Equal As Integers    ${response.status_code}    418
