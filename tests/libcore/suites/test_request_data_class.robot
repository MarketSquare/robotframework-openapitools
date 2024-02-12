*** Settings ***
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${root}/tests/user_implemented/custom_user_mappings.py
Variables       ${root}/tests/variables.py


*** Variables ***
${ORIGIN}=      http://localhost:8000


*** Test Cases ***
Test Has Optional Properties
    ${request_data}=    Get Request Data    endpoint=/employees    method=get
    Should Be Equal    ${request_data.has_optional_properties}    ${FALSE}

    ${request_data}=    Get Request Data    endpoint=/employees    method=post
    Should Be Equal    ${request_data.has_optional_properties}    ${TRUE}

Test Has Optional Params
    ${request_data}=    Get Request Data    endpoint=/available_employees    method=get
    Should Be Equal    ${request_data.has_optional_params}    ${FALSE}

    ${request_data}=    Get Request Data    endpoint=/energy_label/{zipcode}/{home_number}    method=get
    Should Be Equal    ${request_data.has_optional_params}    ${TRUE}

Test Has Optional Headers
    ${request_data}=    Get Request Data    endpoint=/employees    method=get
    Should Be Equal    ${request_data.has_optional_headers}    ${FALSE}

    ${request_data}=    Get Request Data    endpoint=/    method=get
    Should Be Equal    ${request_data.has_optional_headers}    ${TRUE}

Test Params That Can Be Invalidated
    ${request_data}=    Get Request Data    endpoint=/available_employees    method=get
    ${params}=    Set Variable    ${request_data.params_that_can_be_invalidated}
    Should Contain    ${params}    weekday

    ${request_data}=    Get Request Data    endpoint=/energy_label/{zipcode}/{home_number}    method=get
    ${params}=    Set Variable    ${request_data.params_that_can_be_invalidated}
    Should Contain    ${params}    extension

    ${request_data}=    Get Request Data    endpoint=/events/    method=get
    ${params}=    Set Variable    ${request_data.params_that_can_be_invalidated}
    Should Be Empty    ${params}

Test Headers That Can Be Invalidated
    ${request_data}=    Get Request Data    endpoint=/    method=get
    ${headers}=    Set Variable    ${request_data.headers_that_can_be_invalidated}
    Should Be Empty    ${headers}

    ${request_data}=    Get Request Data    endpoint=/secret_message    method=get
    ${headers}=    Set Variable    ${request_data.headers_that_can_be_invalidated}
    Should Contain    ${headers}    secret-code

Test Get Required Properties Dict
    ${request_data}=    Get Request Data    endpoint=/employees    method=post
    Should Contain    ${request_data.dto.as_dict()}    parttime_day
    Should Not Be Empty    ${request_data.dto.name}
    ${required_properties}=    Set Variable    ${request_data.get_required_properties_dict()}
    Should Not Contain    ${required_properties}    parttime_day
    Should Contain    ${required_properties}    name

Test Get Required Params
    ${request_data}=    Get Request Data    endpoint=/available_employees    method=get
    Should Not Be Empty    ${request_data.params.get("weekday")}
    ${required_params}=    Set Variable    ${request_data.get_required_params()}
    Should Contain    ${required_params}    weekday

    ${request_data}=    Get Request Data    endpoint=/energy_label/{zipcode}/{home_number}    method=get
    Should Contain    ${request_data.params}    extension
    ${required_params}=    Set Variable    ${request_data.get_required_params()}
    Should Be Empty    ${required_params}

Test Get Required Headers
    ${request_data}=    Get Request Data    endpoint=/secret_message    method=get
    Should Be Equal As Integers    ${request_data.headers.get("secret-code")}    42
    ${required_headers}=    Set Variable    ${request_data.get_required_headers()}
    Should Contain    ${required_headers}    secret-code
    Should Not Contain    ${required_headers}    seal

    ${request_data}=    Get Request Data    endpoint=/    method=get
    Should Not Be Empty    ${request_data.headers.get("name-from-header")}
    Should Not Be Empty    ${request_data.headers.get("title")}
    ${required_headers}=    Set Variable    ${request_data.get_required_headers()}
    Should Be Empty    ${required_headers}
