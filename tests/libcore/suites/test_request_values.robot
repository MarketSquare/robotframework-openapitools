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
Test Requests Using RequestValues
    ${request_values}=    Get Request Values    path=/employees    method=POST
    ${request_values_dict}=    Convert Request Values To Dict    ${request_values}

    ${response_using_request_values}=    Perform Authorized Request    request_values=${request_values}
    Should Be Equal As Integers    ${response_using_request_values.status_code}    201

    ${response_using_dict}=    Authorized Request    &{request_values_dict}
    Should Be Equal As Integers    ${response_using_dict.status_code}    201

    VAR    ${response_dict_using_request_values}=    ${response_using_request_values.json()}
    VAR    ${response_dict_using_request_values_dict}=    ${response_using_dict.json()}

    Should Not Be Equal
    ...    ${response_dict_using_request_values}[identification]
    ...    ${response_dict_using_request_values_dict}[identification]
    Should Not Be Equal
    ...    ${response_dict_using_request_values}[employee_number]
    ...    ${response_dict_using_request_values_dict}[employee_number]

    Remove From Dictionary    ${response_dict_using_request_values}    identification    employee_number
    Remove From Dictionary    ${response_dict_using_request_values_dict}    identification    employee_number

    Should Be Equal    ${response_dict_using_request_values}    ${response_dict_using_request_values_dict}

    ${request_values_object}=    Get Request Values Object    &{request_values_dict}

    Perform Validated Request    path=/employees    status_code=201    request_values=${request_values_object}
    Validated Request    path=/employees    status_code=201    &{request_values_dict}
