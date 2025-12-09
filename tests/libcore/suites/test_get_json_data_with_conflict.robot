*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py


*** Variables ***
${ORIGIN}       http://localhost:8000


*** Test Cases ***
Test Get Json Data With Conflict Raises For No UniquePropertyValueConstraint
    # No mapping for /wagegroups GET will yield a default constraint_mapping on the request_data
    ${request_data}=    Get Request Data    path=/wagegroups    method=get
    ${url}=    Get Valid Url    path=/wagegroups
    Run Keyword And Expect Error    ValueError: No UniquePropertyValueConstraint*
    ...    Get Json Data With Conflict
    ...    url=${url}
    ...    method=post
    ...    json_data=&{EMPTY}
    ...    constraint_mapping=${request_data.constraint_mapping}
    ...    conflict_status_code=418

Test Get Json Data With Conflict For Post Request
    ${url}=    Get Valid Url    path=/wagegroups
    ${request_data}=    Get Request Data    path=/wagegroups    method=post
    ${invalid_data}=    Get Json Data With Conflict
    ...    url=${url}
    ...    method=post
    ...    json_data=${request_data.valid_data}
    ...    constraint_mapping=${request_data.constraint_mapping}
    ...    conflict_status_code=418
    Should Not Be Empty    ${invalid_data}

Test Get Json Data With Conflict For Put Request
    ${url}=    Get Valid Url    path=/wagegroups/{wagegroup_id}
    ${request_data}=    Get Request Data    path=/wagegroups/{wagegroup_id}    method=put
    ${invalid_json}=    Get Json Data With Conflict
    ...    url=${url}
    ...    method=put
    ...    json_data=${request_data.valid_data}
    ...    constraint_mapping=${request_data.constraint_mapping}
    ...    conflict_status_code=418
    ${response}=    Authorized Request
    ...    url=${url}    method=put    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    418

# Test Get Json Data With Conflict For Patch Request
#    ${url}=    Get Valid Url    path=/wagegroups/{wagegroup_id}
#    ${request_data}=    Get Request Data    path=/wagegroups/{wagegroup_id}    method=put
#    ${invalid_json}=    Get Json Data With Conflict
#    ...    url=${url}
#    ...    method=put
#    ...    constraint_mapping=${request_data.constraint_mapping}
#    ...    conflict_status_code=418
#    ${response}=    Authorized Request
#    ...    url=${url}    method=put    json_data=${invalid_json}
#    Should Be Equal As Integers    ${response.status_code}    418
