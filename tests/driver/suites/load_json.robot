*** Settings ***
Library             OpenApiDriver
...                     source=${ROOT}/tests/files/petstore_openapi.json
...                     ignored_responses=${IGNORED_RESPONSES}
...                     ignored_testcases=${IGNORED_TESTS}
...                     mappings_path=${ROOT}/tests/user_implemented    # library can load with invalid mappings_path

Test Template       Do Nothing


*** Variables ***
@{IGNORED_RESPONSES}        200    404    400
${IGNORE_POST_PET}          ${{("/pet", "POST", 405)}}
${IGNORE_POST_PET_ID}       ${{("/pet/{petId}", "post", 405)}}
${IGNORE_POST_ORDER}        ${{("/store/order", "post", 405)}}
@{IGNORED_TESTS}            ${IGNORE_POST_PET}    ${IGNORE_POST_PET_ID}    ${IGNORE_POST_ORDER}


*** Test Cases ***
# robotcode: ignore[ModelError, VariableNotReplaced]
OpenApiJson test for ${method} on ${path} where ${status_code} is expected


*** Keywords ***
Do Nothing
    [Arguments]    ${path}    ${method}    ${status_code}    # robocop: off=unused-argument
    No Operation
