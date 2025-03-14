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
Test Get Request Data For Invalid Method On Endpoint
    ${request_data}=    Get Request Data    path=/events/    method=delete
    VAR    &{dict}=    &{EMPTY}
    VAR    @{list}=    @{EMPTY}
    Should Be Equal    ${request_data.dto}    ${DEFAULT_DTO()}
    Should Be Equal    ${request_data.dto_schema}    ${dict}
    Should Be Equal    ${request_data.parameters}    ${list}
    Should Be Equal    ${request_data.params}    ${dict}
    Should Be Equal    ${request_data.headers}    ${dict}
    Should Not Be True    ${request_data.has_body}

Test Get Request Data For Endpoint With RequestBody
    ${request_data}=    Get Request Data    path=/employees    method=post
    VAR    &{dict}=    &{EMPTY}
    VAR    @{list}=    @{EMPTY}
    VAR    @{birthdays}=    1970-07-07    1980-08-08    1990-09-09
    VAR    @{parttime_days}=    Monday    Tuesday    Wednesday    Thursday    Friday    ${NONE}
    Length Should Be    ${request_data.dto.name}    36
    Length Should Be    ${request_data.dto.wagegroup_id}    36
    Should Contain    ${birthdays}    ${request_data.dto.date_of_birth}
    Should Contain    ${parttime_days}    ${request_data.dto.parttime_day}
    Should Not Be Empty    ${request_data.dto_schema}
    Should Be Equal    ${request_data.parameters}    ${list}
    Should Be Equal    ${request_data.params}    ${dict}
    VAR    &{expected_headers}=    content-type=application/json
    Should Be Equal    ${request_data.headers}    ${expected_headers}
    Should Be True    ${request_data.has_body}

Test Get Request Data For Endpoint Without RequestBody But With DtoClass
    ${request_data}=    Get Request Data    path=/wagegroups/{wagegroup_id}    method=delete
    VAR    &{dict}=    &{EMPTY}
    Should Be Equal As Strings    ${request_data.dto}    delete_wagegroup_wagegroups__wagegroup_id__delete()
    Should Be Equal    ${request_data.dto_schema}    ${dict}
    Should Not Be Empty    ${request_data.parameters}
    Should Be Equal    ${request_data.params}    ${dict}
    Should Be Equal    ${request_data.headers}    ${dict}
    Should Not Be True    ${request_data.has_body}

# Test Get Request Data For Endpoint With RequestBody With Only Ignored Properties
#    ${request_data}=    Get Request Data    path=/wagegroups/{wagegroup_id}    method=delete
#    VAR    &{dict}=    &{EMPTY}
#    VAR    @{list}=    @{EMPTY}
#    Should Be Equal As Strings    ${request_data.dto}    delete_wagegroup_wagegroups__wagegroup_id__delete()
#    Should Be Equal    ${request_data.dto_schema}    ${dict}
#    Should Not Be Empty    ${request_data.parameters}
#    Should Be Equal    ${request_data.params}    ${dict}
#    VAR    &{expected_headers}=    content-type=application/json
#    Should Be Equal    ${request_data.headers}    ${expected_headers}
#    Should Be True    ${request_data.has_body}
