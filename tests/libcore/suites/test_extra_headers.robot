*** Settings ***
Variables       ${root}/tests/variables.py
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
...                 security_token=secret
...                 extra_headers=${EXTRA_HEADERS}


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Authorized Request With Security Token And Extra Headers
    ${request_data}=    Get Request Data    endpoint=/secret_message    method=get
    ${response}=    Authorized Request
    ...    url=${ORIGIN}/secret_message    method=get    headers=${request_data.headers}
    Should Be Equal As Integers    ${response.status_code}    200
    Should Be True    $EXTRA_HEADERS.items() <= $response.request.headers.items()
    ${TOKEN_HEADER}=    Create Dictionary    Authorization=secret
    Should Be True    $TOKEN_HEADER.items() <= $response.request.headers.items()
