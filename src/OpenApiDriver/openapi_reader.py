"""Module holding the OpenApiReader reader_class implementation."""

from typing import Sequence

from DataDriver.AbstractReaderClass import AbstractReaderClass
from DataDriver.ReaderConfig import TestCaseData

from OpenApiLibCore.models import PathItemObject


class Test:
    """
    Helper class to support ignoring endpoint responses when generating the test cases.
    """

    def __init__(self, path: str, method: str, response: str | int) -> None:
        self.path = path
        self.method = method.lower()
        self.response = str(response)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return (
            self.path == other.path
            and self.method == other.method
            and self.response == other.response
        )


class OpenApiReader(AbstractReaderClass):
    """Implementation of the reader_class used by DataDriver."""

    def get_data_from_source(self) -> list[TestCaseData]:
        test_data: list[TestCaseData] = []

        read_paths_method = getattr(self, "read_paths_method")
        paths: dict[str, PathItemObject] = read_paths_method()
        self._filter_paths(paths)

        ignored_responses_ = [
            str(response) for response in getattr(self, "ignored_responses", [])
        ]

        ignored_tests = [Test(*test) for test in getattr(self, "ignored_testcases", [])]

        for path, path_item in paths.items():
            path_operations = path_item.get_operations()

            # by reseversing the items, post/put operations come before get and delete
            for method, operation_data in reversed(path_operations.items()):
                tags_from_spec = operation_data.tags
                for response in operation_data.responses.keys():
                    # 'default' applies to all status codes that are not specified, in
                    # which case we don't know what to expect and therefore can't verify
                    if (
                        response == "default"
                        or response in ignored_responses_
                        or Test(path, method, response) in ignored_tests
                    ):
                        continue

                    tag_list = _get_tag_list(
                        tags=tags_from_spec, method=method, response=response
                    )
                    test_data.append(
                        TestCaseData(
                            arguments={
                                "${path}": path,
                                "${method}": method.upper(),
                                "${status_code}": response,
                            },
                            tags=tag_list,
                        ),
                    )
        return test_data

    def _filter_paths(self, paths: dict[str, PathItemObject]) -> None:
        def matches_include_pattern(path: str) -> bool:
            for included_path in included_paths:
                if path == included_path:
                    return True
                if included_path.endswith("*"):
                    wildcard_include, _, _ = included_path.partition("*")
                    if path.startswith(wildcard_include):
                        return True
            return False

        def matches_ignore_pattern(path: str) -> bool:
            for ignored_path in ignored_paths:
                if path == ignored_path:
                    return True

                if ignored_path.endswith("*"):
                    wildcard_ignore, _, _ = ignored_path.partition("*")
                    if path.startswith(wildcard_ignore):
                        return True
            return False

        if included_paths := getattr(self, "included_paths", ()):
            path_list = list(paths.keys())
            for path in path_list:
                if not matches_include_pattern(path):
                    paths.pop(path)

        if ignored_paths := getattr(self, "ignored_paths", ()):
            path_list = list(paths.keys())
            for path in path_list:
                if matches_ignore_pattern(path):
                    paths.pop(path)


def _get_tag_list(tags: Sequence[str], method: str, response: str) -> list[str]:
    return [*tags, f"Method: {method.upper()}", f"Response: {response}"]
