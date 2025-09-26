from robot.api.deco import library
from robot.api.interfaces import ListenerV3
from robot.libraries.BuiltIn import BuiltIn
from robot.result.model import Keyword as KeywordResult
from robot.running.model import Keyword as KeywordData

run_keyword = BuiltIn().run_keyword


@library
class EtagListener(ListenerV3):
    def __init__(self) -> None:
        self.ROBOT_LIBRARY_LISTENER = self

    def start_keyword(self, data: KeywordData, result: KeywordResult) -> None:
        # NOTE: data.args and result.args reference the same tuple (i.e.
        # id(data.args) == id(result.args)) so we only have to update one.
        name = result.name
        if name != "Authorized Request":
            return

        url = result.args[0]
        method = result.args[1]
        params = result.args[2]
        headers = result.args[3]

        if method != "PATCH":
            return

        current_etag = result.args[3].get("If-Match", "not an etag")
        # NOTE: This value is hard-coded in the custom_user_mappings.py
        if current_etag == "not an etag":
            return

        get_result = run_keyword("authorized_request", url, "GET", params, headers)
        etag = get_result.headers.get("etag")
        result.args[3]["If-Match"] = etag
