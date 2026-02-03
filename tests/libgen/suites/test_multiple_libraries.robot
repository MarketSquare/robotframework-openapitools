*** Settings ***
Library         MyGeneratedLibrary
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
Library         MyGeneratedLibrary
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
...             AS    MyDuplicate
Library         MyOtherGeneratedLibrary
...                 source=${ORIGIN}/openapi.json
...                 origin=${ORIGIN}
...                 base_path=${EMPTY}
...                 mappings_path=${ROOT}/tests/user_implemented/custom_user_mappings.py
Library         MyGeneratedEdgeCaseLibrary
...                 source=${ROOT}/tests/files/schema_with_parameter_name_duplication.yaml
...                 origin=${ORIGIN}
...             AS    EdgeCases

Test Tags       rf7


*** Variables ***
${ORIGIN}       http://localhost:8000


*** Test Cases ***
Test Libraries From Same Spec
    ${first_url}=    MyGeneratedLibrary.Get Valid Url    path=/employees
    ${second_url}=    MyOtherGeneratedLibrary.Get Valid Url    path=/employees
    Should Be Equal As Strings    ${first_url}    ${second_url}

    ${first_values}=    MyGeneratedLibrary.Get Request Values    path=/employees    method=POST
    VAR    ${first_json}=    ${first_values.json_data}
    ${second_values}=    MyDuplicate.Get Request Values    path=/employees    method=POST
    VAR    ${second_json}=    ${second_values.json_data}
    ${third_values}=    MyOtherGeneratedLibrary.Get Request Values    path=/employees    method=POST
    VAR    ${third_json}=    ${third_values.json_data}
    Should Be Equal    ${first_json.keys()}    ${second_json.keys()}
    Should Be Equal    ${second_json.keys()}    ${third_json.keys()}

    Get Employees
    Run Keyword And Expect Error    Multiple keywords with name 'Get Employees Employees Get' found. *
    ...    Get Employees Employees Get    # robotcode: ignore[MultipleKeywords]
    MyGeneratedLibrary.Get Employees Employees Get
    MyDuplicate.Get Employees Employees Get

Test Import Alias
    Run Keyword And Expect Error    Failed to get a valid id using GET on http://localhost:8000/hypermedia
    ...    Get Hypermedia Name
