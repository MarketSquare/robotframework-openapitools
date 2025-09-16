*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         String
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Get Invalidated Parameters Raises For Empty Parameters List
    ${request_data}=    Get Request Data    path=/secret_message    method=get
    Evaluate    ${request_data.parameters.clear()} is None
    Run Keyword And Expect Error    ValueError: No params or headers to invalidate.
    ...    Get Invalidated Parameters
    ...    status_code=422
    ...    request_data=${request_data}

Test Get Invalidated Parameters Raises For Mismatched Parameters List
    ${request_data}=    Get Request Data    path=/secret_message    method=get
    Run Keyword And Expect Error    ValueError: No parameter can be changed to cause status_code 402.
    ...    Get Invalidated Parameters
    ...    status_code=402
    ...    request_data=${request_data}

Test Get Invalidated Parameters Raises For Status Code That Cannot Be Invalidated
    ${request_data}=    Get Request Data    path=/secret_message    method=get
    Run Keyword And Expect Error    ValueError: No relations to cause status_code 200 found.
    ...    Get Invalidated Parameters
    ...    status_code=200
    ...    request_data=${request_data}

Test Get Invalidated Parameters Raises For Headers That Cannot Be Invalidated
    ${request_data}=    Get Request Data    path=/    method=get
    Run Keyword And Expect Error    ValueError: None of the query parameters and headers can be invalidated.
    ...    Get Invalidated Parameters
    ...    status_code=422
    ...    request_data=${request_data}

Test Get Invalidated Parameters For Invalid Propery Default Response
    ${request_data}=    Get Request Data    path=/secret_message    method=get
    ${invalidated}=    Get Invalidated Parameters
    ...    status_code=422
    ...    request_data=${request_data}
    ${secret_code}=    Set Variable    ${invalidated[1].get("secret-code")}
    Length Should Be    ${secret_code}    36

Test Get Invalidated Parameters For PropertyValueConstraint
    ${request_data}=    Get Request Data    path=/secret_message    method=get
    ${invalidated}=    Get Invalidated Parameters
    ...    status_code=401
    ...    request_data=${request_data}
    ${secret_code}=    Set Variable    ${invalidated[1].get("secret-code")}
    Should Be True    int($secret_code) != 42

    ${request_data}=    Get Request Data    path=/secret_message    method=get
    ${invalidated}=    Get Invalidated Parameters
    ...    status_code=403
    ...    request_data=${request_data}
    ${seal}=    Set Variable    ${invalidated[1].get("seal")}
    Should Not Be Equal    ${seal}    ${NONE}

Test Get Invalidated Parameters Adds Optional Parameter If Not Provided
    ${request_data}=    Get Request Data    path=/secret_message    method=get
    Evaluate    ${request_data.headers.clear()} is None
    ${invalidated}=    Get Invalidated Parameters
    ...    status_code=422
    ...    request_data=${request_data}
    ${headers}=    Set Variable    ${invalidated[1]}
    Length Should Be    ${headers}    1

Test Get Invalidated Parameters Adds Optional Parameter If treat_as_mandatory Is True
    ${request_data}=    Get Request Data    path=/energy_label/{zipcode}/{home_number}    method=get
    Evaluate    ${request_data.params.clear()} is None
    ${invalidated}=    Get Invalidated Parameters
    ...    status_code=422
    ...    request_data=${request_data}
    ${extension}=    Set Variable    ${invalidated[0].get("extension")}
    Length Should Be    ${extension}    20
