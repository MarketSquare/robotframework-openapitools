*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         OpenApiLibCore
...                 source=${ROOT}/tests/files/schema_with_allof.yaml
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}

Test Tags       rf7


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Get Request Data For Schema With allOf
    ${request_data}=    Get Request Data    path=/hypermedia    method=post
    VAR    &{dict}=    &{EMPTY}
    VAR    @{list}=    @{EMPTY}
    VAR    &{expected_headers}=    content-type=application/hal+json
    Length Should Be    ${request_data.dto.isan}    36
    Length Should Be    ${request_data.dto.published}    10
    Length Should Be    ${request_data.dto.tags}    1
    Length Should Be    ${request_data.dto.tags}[0]    36
    Length Should Be    ${request_data.body_schema.properties.root}    4
    Should Be Equal    ${request_data.parameters}    ${list}
    Should Be Equal    ${request_data.params}    ${dict}
    Should Be Equal    ${request_data.headers}    ${expected_headers}
