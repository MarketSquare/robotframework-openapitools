*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Bool Response
    ${url}=    Get Valid Url    path=/employees/{employee_id}
    ${request_data}=    Get Request Data    path=/employees/{employee_id}    method=patch
    ${response}=    Authorized Request
    ...    url=${url}
    ...    method=patch
    ...    params=${request_data.params}
    ...    headers=${request_data.headers}
    ...    json_data=${request_data.dto.as_dict()}

    Validate Response    path=/employees/{employee_id}    response=${response}
