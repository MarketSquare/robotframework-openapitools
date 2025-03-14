*** Settings ***
Library         OperatingSystem
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
Variables       ${root}/tests/variables.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Get Invalid Json Data Raises If Data Cannot Be Invalidated
    ${request_data}=    Get Request Data    path=/    method=get
    Run Keyword And Expect Error    ValueError: Failed to invalidate: no data_relations and empty schema.
    ...    Get Invalid Json Data
    ...    url=none
    ...    method=none
    ...    status_code=999
    ...    request_data=${request_data}

    ${request_data}=    Get Request Data    path=/employees    method=post
    Run Keyword And Expect Error    ValueError: No property can be invalidated to cause status_code 999
    ...    Get Invalid Json Data
    ...    url=none
    ...    method=none
    ...    status_code=999
    ...    request_data=${request_data}

Test Get Invalid Json Data Based On Schema
    ${request_data}=    Get Request Data    path=/events/    method=post
    Should Be Empty    ${request_data.dto.get_relations_for_error_code(422)}
    ${invalid_json}=    Get Invalid Json Data
    ...    url=none
    ...    method=none
    ...    status_code=422
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto}
    ${response}=    Authorized Request
    ...    url=${ORIGIN}/events/    method=post    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    422

Test Get Invalid Json Data For UniquePropertyValueConstraint
    ${request_data}=    Get Request Data    path=/wagegroups    method=post
    ${invalid_json}=    Get Invalid Json Data
    ...    url=${ORIGIN}/wagegroups
    ...    method=post
    ...    status_code=418
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto}
    ${response}=    Authorized Request
    ...    url=${ORIGIN}/wagegroups    method=post    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    418

Test Get Invalid Json Data For IdReference
    ${url}=    Get Valid Url    path=/wagegroups/{wagegroup_id}    method=delete
    ${request_data}=    Get Request Data    path=/wagegroups/{wagegroup_id}    method=delete
    ${invalid_json}=    Get Invalid Json Data
    ...    url=${url}
    ...    method=delete
    ...    status_code=406
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto}
    ${response}=    Authorized Request
    ...    url=${url}    method=delete    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    406

Test Get Invalid Json Data For IdDependency
    ${url}=    Get Valid Url    path=/employees    method=post
    ${request_data}=    Get Request Data    path=/employees    method=post
    ${invalid_json}=    Get Invalid Json Data
    ...    url=${url}
    ...    method=post
    ...    status_code=451
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto}
    ${response}=    Authorized Request
    ...    url=${url}    method=post    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    451

Test Get Invalid Json Data For Dto With Other Relations
    ${request_data}=    Get Request Data    path=/employees    method=post
    ${invalid_json}=    Get Invalid Json Data
    ...    url=${ORIGIN}/employees
    ...    method=post
    ...    status_code=403
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto}
    ${response}=    Authorized Request
    ...    url=${ORIGIN}/employees    method=post    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    403

Test Get Invalid Json Data Can Invalidate Missing Optional Parameters
    ${url}=    Get Valid Url    path=/employees/{emplyee_id}    method=patch
    ${request_data}=    Get Request Data    path=/employees/{emplyee_id}    method=patch
    Evaluate    ${request_data.dto.__dict__.clear()} is None
    ${invalid_json}=    Get Invalid Json Data
    ...    url=${url}
    ...    method=patch
    ...    status_code=422
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto.as_dict()}
    ${response}=    Authorized Request
    ...    url=${url}    method=patch    json_data=${invalid_json}
    VAR    @{expected_status_codes}=    ${403}    ${422}    ${451}
    Should Contain    ${expected_status_codes}    ${response.status_code}
