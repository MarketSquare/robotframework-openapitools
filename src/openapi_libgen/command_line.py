import argparse
from pathlib import Path

from openapi_libgen import generator
from openapi_libgen.parsing_utils import remove_unsafe_characters_from_string

parser = argparse.ArgumentParser(
    prog="openapi_libgen",
    description="The OpenApiTools library generator",
    epilog="Inspired by roboswag. Thank you Bartlomiej and Mateusz for your work!",
)
parser.add_argument("-s", "--source")
parser.add_argument("-d", "--destination")
parser.add_argument("-n", "--name")
parser.add_argument("--recursion-limit", default=1, type=int)
parser.add_argument("--recursion-default", default={})
args = parser.parse_args()


def get_class_and_module_name_from_string(string: str) -> tuple[str, str]:
    safe_string = remove_unsafe_characters_from_string(string)
    class_name = safe_string.replace("_", "")
    module_name = safe_string.lower()
    return class_name, module_name


def main() -> None:
    if not (source := args.source):
        source = input("Please provide a source for the generation: ")

    spec = generator.load_openapi_spec(
        source=source,
        recursion_limit=args.recursion_limit,
        recursion_default=args.recursion_default,
    )

    if not (destination := args.destination):
        destination = input(
            "Please provide a path to where the library will be generated: "
        )
    path = Path(destination)

    if args.name:
        safe_library_name, safe_module_name = get_class_and_module_name_from_string(
            args.name
        )
    else:
        default_name = spec.info.title

        default_library_name, default_module_name = (
            get_class_and_module_name_from_string(default_name)
        )

        library_name = (
            input(
                f"Please provide a name for the library [default: {default_library_name}]: "
            )
            or default_library_name
        )
        if library_name != default_library_name:
            safe_library_name, safe_module_name = get_class_and_module_name_from_string(
                library_name
            )
        else:
            safe_library_name, safe_module_name = (
                default_library_name,
                default_module_name,
            )

    generator.generate(
        openapi_object=spec,
        output_folder=path,
        library_name=safe_library_name,
        module_name=safe_module_name,
    )
