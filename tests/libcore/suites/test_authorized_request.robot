*** Settings ***
Library         OpenApiLibCore
...                 source=${origin}/openapi.json
...                 origin=${origin}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
Variables       ${ROOT}/tests/variables.py


*** Variables ***
${origin}=      http://localhost:8000


*** Test Cases ***
Test Authorized Request Without Authorization
    ${response}=    Authorized Request    url=${origin}/    method=get
    Should Be Equal As Integers    ${response.status_code}    200

# Test Authorized Request With Username And Password
#    ${response}=    Authorized Request    url=${origin}/    method=get
#    Should Be Equal As Integers    ${response.status_code}    200

# Test Authorized Request With Requests Auth Object
#    ${response}=    Authorized Request    url=${origin}/    method=get
#    Should Be Equal As Integers    ${response.status_code}    200

# Test Authorized Request With Authorization Token
#    ${response}=    Authorized Request    url=${origin}/    method=get
#    Should Be Equal As Integers    ${response.status_code}    200
