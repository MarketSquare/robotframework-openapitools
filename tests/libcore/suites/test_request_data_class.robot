*** Settings ***
Variables       ${ROOT}/tests/variables.py
Library         OpenApiLibCore
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py

Test Tags       rf7


*** Variables ***
${ORIGIN}       http://localhost:8000


*** Test Cases ***
Test Has Optional Properties
    ${request_data}=    Get Request Data    path=/employees    method=get
    Should Be Equal    ${request_data.has_optional_properties}    ${FALSE}

    ${request_data}=    Get Request Data    path=/employees    method=post
    Should Be Equal    ${request_data.has_optional_properties}    ${TRUE}

Test Has Optional Params
    ${request_data}=    Get Request Data    path=/available_employees    method=get
    Should Be Equal    ${request_data.has_optional_params}    ${FALSE}

    ${request_data}=    Get Request Data    path=/energy_label/{zipcode}/{home_number}    method=get
    Should Be Equal    ${request_data.has_optional_params}    ${TRUE}

Test Has Optional Headers
    ${request_data}=    Get Request Data    path=/employees    method=get
    Should Be Equal    ${request_data.has_optional_headers}    ${FALSE}

    ${request_data}=    Get Request Data    path=/    method=get
    Should Be Equal    ${request_data.has_optional_headers}    ${TRUE}

Test Params That Can Be Invalidated
    ${request_data}=    Get Request Data    path=/available_employees    method=get
    VAR    ${params}=    ${request_data.params_that_can_be_invalidated}
    Should Contain    ${params}    weekday

    ${request_data}=    Get Request Data    path=/energy_label/{zipcode}/{home_number}    method=get
    VAR    ${params}=    ${request_data.params_that_can_be_invalidated}
    Should Contain    ${params}    extension

    ${request_data}=    Get Request Data    path=/events/    method=get
    VAR    ${params}=    ${request_data.params_that_can_be_invalidated}
    Should Be Empty    ${params}

Test Headers That Can Be Invalidated
    ${request_data}=    Get Request Data    path=/    method=get
    VAR    ${headers}=    ${request_data.headers_that_can_be_invalidated}
    Should Be Empty    ${headers}

    ${request_data}=    Get Request Data    path=/secret_message    method=get
    VAR    ${headers}=    ${request_data.headers_that_can_be_invalidated}
    Should Contain    ${headers}    secret-code

Test Get Required Properties Dict
    ${request_data}=    Get Request Data    path=/employees    method=post
    Should Contain    ${request_data.dto.as_dict()}    parttime_schedule
    Should Not Be Empty    ${request_data.dto.name}
    VAR    ${required_properties}=    ${request_data.get_required_properties_dict()}
    Should Contain    ${required_properties}    name
    # parttime_schedule is configured with treat_as_mandatory=True
    Should Contain    ${required_properties}    parttime_schedule

Test Get Required Params
    ${request_data}=    Get Request Data    path=/available_employees    method=get
    Should Not Be Empty    ${request_data.params.get("weekday")}
    VAR    ${required_params}=    ${request_data.get_required_params()}
    Should Contain    ${required_params}    weekday

    ${request_data}=    Get Request Data    path=/energy_label/{zipcode}/{home_number}    method=get
    Should Contain    ${request_data.params}    extension
    VAR    ${required_params}=    ${request_data.get_required_params()}
    # extension is configured with treat_as_mandatory=True
    Should Contain    ${required_params}    extension

Test Get Required Headers
    ${request_data}=    Get Request Data    path=/secret_message    method=get
    Should Be Equal As Integers    ${request_data.headers.get("secret-code")}    42
    VAR    ${required_headers}=    ${request_data.get_required_headers()}
    Should Contain    ${required_headers}    secret-code
    Should Not Contain    ${required_headers}    seal

    ${request_data}=    Get Request Data    path=/    method=get
    Should Not Be Empty    ${request_data.headers.get("name-from-header")}
    Should Not Be Empty    ${request_data.headers.get("title")}
    VAR    ${required_headers}=    ${request_data.get_required_headers()}
    Should Be Empty    ${required_headers}
