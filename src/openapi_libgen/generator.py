import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from prance import ResolvingParser

from openapi_libgen.spec_parser import get_keyword_data
from OpenApiLibCore.models import OpenApiObject

HERE = Path(__file__).parent.resolve()
INIT_TEMPLATE_PATH = HERE / "templates/__init__.jinja"
LIBRARY_TEMPLATE_PATH = HERE / "templates/library.jinja"


def load_openapi_spec(
    source: str, recursion_limit: int, recursion_default: object
) -> OpenApiObject:
    def recursion_limit_handler(
        limit: int, refstring: str, recursions: object
    ) -> object:  # pylint: disable=unused-argument
        return recursion_default

    parser = ResolvingParser(
        source,
        backend="openapi-spec-validator",
        recursion_limit=recursion_limit,
        recursion_limit_handler=recursion_limit_handler,
    )
    assert parser.specification is not None, (
        "Source was loaded, but no specification was present after parsing."
    )
    openapi_object = OpenApiObject.model_validate(parser.specification)
    return openapi_object


def generate(
    openapi_object: OpenApiObject,
    output_folder: Path,
    library_name: str,
    module_name: str,
) -> str:
    keyword_data = get_keyword_data(openapi_object=openapi_object)

    library_folder = output_folder / library_name
    library_folder.mkdir(parents=True, exist_ok=True)

    environment = Environment(loader=FileSystemLoader(f"{HERE}/templates/"))

    init_template = environment.get_template("__init__.jinja")
    init_path = library_folder / "__init__.py"
    init_content = init_template.render(
        library_name=library_name,
        module_name=module_name,
    )
    with open(init_path, mode="w", encoding="utf-8") as init_file:
        init_file.write(init_content)
        print(f"{init_path} created")

    library_template = environment.get_template("library.jinja")
    module_path = library_folder / f"{module_name}.py"
    library_content = library_template.render(
        library_name=library_name,
        keywords=keyword_data,
    )
    with open(module_path, mode="w", encoding="utf-8") as library_file:
        library_file.write(library_content)
        print(f"{module_path} created")

    return f"Generated {library_name} at {output_folder.resolve().as_posix()}/{module_name}"


if __name__ == "__main__":
    source = sys.argv[1]
    destination = Path(sys.argv[2])
    library_name = sys.argv[3]
    module_name = sys.argv[4]
    spec = load_openapi_spec(source=source, recursion_limit=1, recursion_default={})

    result_string = generate(
        openapi_object=spec,
        output_folder=destination,
        library_name=library_name,
        module_name=module_name,
    )
