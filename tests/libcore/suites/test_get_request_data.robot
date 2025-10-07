*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         Collections
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py

Test Tags       rf7


*** Variables ***
${ORIGIN}       http://localhost:8000


*** Test Cases ***
Test Get Request Data For Invalid Method On Endpoint
    ${request_data}=    Get Request Data    path=/events/    method=delete
    VAR    &{dict}=    &{EMPTY}
    VAR    @{list}=    @{EMPTY}
    Should Be Equal    ${request_data.dto.__doc__}    DeleteEvents()
    Should Be Equal    ${request_data.body_schema}    ${NONE}
    Should Be Equal    ${request_data.parameters}    ${list}
    Should Be Equal    ${request_data.params}    ${dict}
    Should Be Equal    ${request_data.headers}    ${dict}
    Should Not Be True    ${request_data.has_body}

Test Get Request Data For Endpoint With Object RequestBody
    ${request_data}=    Get Request Data    path=/employees    method=post
    VAR    &{dict}=    &{EMPTY}
    VAR    @{list}=    @{EMPTY}
    VAR    @{birthdays}=    1970-07-07    1980-08-08    1990-09-09
    VAR    @{weekdays}=    Monday    Tuesday    Wednesday    Thursday    Friday
    Length Should Be    ${request_data.dto.name}    36
    Length Should Be    ${request_data.dto.wagegroup_id}    36
    Should Contain    ${birthdays}    ${request_data.dto.date_of_birth}
    VAR    ${generated_parttime_schedule}=    ${request_data.dto.parttime_schedule}
    IF    $generated_parttime_schedule is not None
        ${parttime_days}=    Get From Dictionary    ${generated_parttime_schedule}    parttime_days
        Should Be True    1 <= len($parttime_days) <= 5
        FOR    ${parttime_day}    IN    @{parttime_days}
            ${weekday}=    Get From Dictionary    ${parttime_day}    weekday
            Should Contain    ${weekdays}    ${weekday}
            ${available_hours}=    Get From Dictionary    ${parttime_day}    available_hours
            Should Be True    0 <= $available_hours < 8
        END
    END
    Should Not Be Empty    ${request_data.body_schema.properties.root}
    Should Be Equal    ${request_data.parameters}    ${list}
    Should Be Equal    ${request_data.params}    ${dict}
    VAR    &{expected_headers}=    content-type=application/json
    Should Be Equal    ${request_data.headers}    ${expected_headers}
    Should Be True    ${request_data.has_body}

Test Get Request Data For Endpoint With Array Request Body
    VAR    ${empty_array_seen}=    ${FALSE}
    VAR    ${non_empty_array_seen}=    ${FALSE}
    WHILE    not ($empty_array_seen and $non_empty_array_seen)    limit=10
        ${request_data}=    Get Request Data    path=/events/    method=put
        TRY
            VAR    ${first_valid_item}=    ${request_data.valid_data[0]}
            Dictionary Should Contain Key    ${first_valid_item}    message
            Dictionary Should Contain Key    ${first_valid_item}    details
            List Should Not Contain Duplicates    ${first_valid_item}[details]
            VAR    ${non_empty_array_seen}=    ${TRUE}
        EXCEPT    * IndexError: list index out of range    type=glob
            Should Be Equal    ${request_data.body_schema.type}    array
            Should Be Equal As Strings    ${request_data.dto}    <class 'abc.put_events_events__put'>
            VAR    ${empty_array_seen}=    ${TRUE}
        END
    END

Test Get Request Data For Endpoint Without RequestBody But With DtoClass
    ${request_data}=    Get Request Data    path=/wagegroups/{wagegroup_id}    method=delete
    VAR    &{dict}=    &{EMPTY}
    Should Be Equal As Strings
    ...    ${request_data.dto}
    ...    <class 'abc.delete_wagegroup_wagegroups__wagegroup_id__delete'>
    Should Be Equal    ${request_data.body_schema}    ${NONE}
    Should Not Be Empty    ${request_data.parameters}
    Should Be Equal    ${request_data.params}    ${dict}
    Should Be Equal    ${request_data.headers}    ${dict}
    Should Not Be True    ${request_data.has_body}
