*** Settings ***
Library         OpenApiLibCore
...                 source=${origin}/openapi.json
...                 origin=${origin}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
Library         OperatingSystem
Variables       ${root}/tests/variables.py


*** Variables ***
${origin}=      http://localhost:8000


*** Test Cases ***
Test Get Invalid Json Data Raises If Data Cannot Be Invalidated
    ${request_data}=    Get Request Data    endpoint=/    method=get
    Run Keyword And Expect Error    ValueError: Failed to invalidate: no data_relations and empty schema.
    ...    Get Invalid Json Data
    ...    url=none
    ...    method=none
    ...    status_code=999
    ...    request_data=${request_data}

    ${request_data}=    Get Request Data    endpoint=/employees    method=post
    Run Keyword And Expect Error    ValueError: No property can be invalidated to cause status_code 999
    ...    Get Invalid Json Data
    ...    url=none
    ...    method=none
    ...    status_code=999
    ...    request_data=${request_data}

Test Get Invalid Json Data Based On Schema
    ${request_data}=    Get Request Data    endpoint=/events/    method=post
    Should Be Empty    ${request_data.dto.get_relations_for_error_code(422)}
    ${invalid_json}=    Get Invalid Json Data
    ...    url=none
    ...    method=none
    ...    status_code=422
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto}
    ${response}=    Authorized Request
    ...    url=${origin}/events/    method=post    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    422

Test Get Invalid Json Data For UniquePropertyValueConstraint
    ${request_data}=    Get Request Data    endpoint=/wagegroups    method=post
    ${invalid_json}=    Get Invalid Json Data
    ...    url=${origin}/wagegroups
    ...    method=post
    ...    status_code=418
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto}
    ${response}=    Authorized Request
    ...    url=${origin}/wagegroups    method=post    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    418

Test Get Invalid Json Data For IdReference
    ${url}=    Get Valid Url    endpoint=/wagegroups/{wagegroup_id}    method=delete
    ${request_data}=    Get Request Data    endpoint=/wagegroups/{wagegroup_id}    method=delete
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
    ${url}=    Get Valid Url    endpoint=/employees    method=post
    ${request_data}=    Get Request Data    endpoint=/employees    method=post
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
    ${request_data}=    Get Request Data    endpoint=/employees    method=post
    ${invalid_json}=    Get Invalid Json Data
    ...    url=${origin}/employees
    ...    method=post
    ...    status_code=403
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto}
    ${response}=    Authorized Request
    ...    url=${origin}/employees    method=post    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    403

Test Get Invalid Json Data Can Invalidate Missing Optional Parameters
    ${request_data}=    Get Request Data    endpoint=/employees/{emplyee_id}    method=patch
    Evaluate    ${request_data.dto.__dict__.clear()} is None
    ${invalid_json}=    Get Invalid Json Data
    ...    url=${origin}/employees/{employee_id}
    ...    method=patch
    ...    status_code=422
    ...    request_data=${request_data}
    Should Not Be Equal    ${invalid_json}    ${request_data.dto}
    ${response}=    Authorized Request
    ...    url=${origin}/employees/{employee_id}    method=patch    json_data=${invalid_json}
    Should Be Equal As Integers    ${response.status_code}    422
