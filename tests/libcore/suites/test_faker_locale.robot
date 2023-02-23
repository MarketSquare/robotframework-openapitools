*** Settings ***
Library         OpenApiLibCore
...                 source=${root}/tests/files/schema_with_allof.yaml
...                 origin=${origin}
...                 base_path=${EMPTY}
...                 faker_locale=zh_CN
Variables       ${root}/tests/variables.py


*** Variables ***
${origin}=      http://localhost:8000


*** Test Cases ***
Test Get Request Data For Schema With allOf
    ${request_data}=    Get Request Data    endpoint=/hypermedia    method=post
    ${dict}=    Create Dictionary
    ${list}=    Create List
    ${list_of_dict}=    Create List    ${dict}
    # this regex should match all characters in the simplified Chinese character set
    Should Match Regexp    ${request_data.dto.title}    ^[\u4E00-\u9FA5]+$
