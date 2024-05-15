*** Settings ***
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
Variables       ${ROOT}/tests/variables.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Bool Response
    ${url}=    Get Valid Url    endpoint=/employees/{employee_id}    method=patch
    ${request_data}=    Get Request Data    endpoint=/employees/{employee_id}    method=patch
    ${response}=    Authorized Request
    ...    url=${url}
    ...    method=patch
    ...    params=${request_data.params}
    ...    headers=${request_data.headers}
    ...    json_data=${request_data.dto.as_dict()}

    Validate Response    path=/employees/{employee_id}    response=${response}
