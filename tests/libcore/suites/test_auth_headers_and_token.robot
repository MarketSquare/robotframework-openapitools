*** Settings ***
Documentation
...                 Note: The tests in this suite are not independent and their order matters.
...                 This is due to the fact that the keywords tested here have a Suite scope
...                 impact, which cannot be tested isolated in a single test case.

Variables           ${root}/tests/variables.py
Library             OpenApiLibCore
...                     source=${ORIGIN}/openapi.json
...                     origin=${ORIGIN}
...                     base_path=${EMPTY}
...                     mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
...                     security_token=secret
...                     extra_headers=${EXTRA_HEADERS}


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Authorized Request With Security Token And Extra Headers
    ${request_data}=    Get Request Data    endpoint=/secret_message    method=get
    ${response}=    Authorized Request
    ...    url=${ORIGIN}/secret_message    method=get    headers=${request_data.headers}
    Should Be Equal As Integers    ${response.status_code}    200

    VAR    ${headers_from_request}    ${response.request.headers}
    FOR    ${key}    ${value}    IN    &{EXTRA_HEADERS}
        Should Be Equal    ${headers_from_request}[${key}]    ${value}
    END

    VAR    ${token_from_header}    ${response.request.headers.get("Authorization")}
    Should Be Equal    ${token_from_header}    secret

Test Set Security Token
    Set Security Token    another secret

    ${request_data}=    Get Request Data    endpoint=/secret_message    method=get
    ${response}=    Authorized Request
    ...    url=${ORIGIN}/secret_message    method=get    headers=${request_data.headers}
    Should Be Equal As Integers    ${response.status_code}    200

    VAR    ${headers_from_request}    ${response.request.headers}
    FOR    ${key}    ${value}    IN    &{EXTRA_HEADERS}
        Should Be Equal    ${headers_from_request}[${key}]    ${value}
    END

    VAR    ${token_from_header}    ${response.request.headers.get("Authorization")}
    Should Be Equal    ${token_from_header}    another secret

Test Set Extra Headers
    Set Extra Headers    {"spam": "bacon"}

    ${request_data}=    Get Request Data    endpoint=/secret_message    method=get
    ${response}=    Authorized Request
    ...    url=${ORIGIN}/secret_message    method=get    headers=${request_data.headers}
    Should Be Equal As Integers    ${response.status_code}    200

    VAR    ${headers_from_request}    ${response.request.headers}
    FOR    ${key}    ${_}    IN    &{EXTRA_HEADERS}
        Should Be Equal    ${headers_from_request.get("${key}")}    ${NONE}
    END
    VAR    ${spam_from_header}    ${response.request.headers.get("spam")}
    Should Be Equal    ${spam_from_header}    bacon

    VAR    ${token_from_header}    ${response.request.headers.get("Authorization")}
    Should Be Equal    ${token_from_header}    another secret

Test Set Basic Auth
    Set Basic Auth    username=Joe    password=Jane

    ${request_data}=    Get Request Data    endpoint=/secret_message    method=get
    ${response}=    Authorized Request
    ...    url=${ORIGIN}/secret_message    method=get    headers=${request_data.headers}
    Should Be Equal As Integers    ${response.status_code}    200

    VAR    ${headers_from_request}    ${response.request.headers}
    FOR    ${key}    ${_}    IN    &{EXTRA_HEADERS}
        Should Be Equal    ${headers_from_request.get("${key}")}    ${NONE}
    END
    VAR    ${spam_from_header}    ${response.request.headers.get("spam")}
    Should Be Equal    ${spam_from_header}    bacon

    VAR    ${token_from_header}    ${response.request.headers.get("Authorization")}
    Should Start With    ${token_from_header}    Basic

Test Set Auth
    Set Auth    auth=${DIGEST_AUTH}

    ${request_data}=    Get Request Data    endpoint=/secret_message    method=get
    ${response}=    Authorized Request
    ...    url=${ORIGIN}/secret_message    method=get    headers=${request_data.headers}
    Should Be Equal As Integers    ${response.status_code}    200

    VAR    ${headers_from_request}    ${response.request.headers}
    FOR    ${key}    ${_}    IN    &{EXTRA_HEADERS}
        Should Be Equal    ${headers_from_request.get("${key}")}    ${NONE}
    END
    VAR    ${spam_from_header}    ${response.request.headers.get("spam")}
    Should Be Equal    ${spam_from_header}    bacon

    Should Not Contain    ${response.request.headers}    Authorization
