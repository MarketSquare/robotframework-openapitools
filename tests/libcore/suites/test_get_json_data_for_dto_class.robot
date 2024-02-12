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
Test Get Json Data For Dto Class With DefaultDto
    ${request_data}=    Get Request Data    endpoint=/wagegroups    method=post
    Get Json Data For Dto Class
    ...    schema=${request_data.dto_schema}
    ...    dto_class=${DEFAULT_DTO}
    ...    operation_id=dummy

Test Get Json Data For Dto Class With IGNORE Constrained
    ${request_data}=    Get Request Data    endpoint=/wagegroups    method=post
    Get Json Data For Dto Class
    ...    schema=${request_data.dto_schema}
    ...    dto_class=${WAGEGROUP_DTO}
    ...    operation_id=dummy

Test Get Json Data For Dto Class With Single DependantId
    ${request_data}=    Get Request Data    endpoint=/employees    method=post
    Get Json Data For Dto Class
    ...    schema=${request_data.dto_schema}
    ...    dto_class=${EMPLOYEE_DTO}
    ...    operation_id=dummy

# Test Get Json Data For Dto Class With Multiple DependantIds
#    ${request_data}=    Get Request Data    endpoint=/employees    method=post
#    Get Json Data For Dto Class
#    ...    schema=${request_data.dto_schema}
#    ...    dto_class=${EMPLOYEE_DTO}
#    ...    operation_id=dummy

Test Get Json Data For Dto Class With Array And Object
    ${request_data}=    Get Request Data    endpoint=/events/    method=post
    Get Json Data For Dto Class
    ...    schema=${request_data.dto_schema}
    ...    dto_class=${DEFAULT_DTO}
    ...    operation_id=dummy
