from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from openapi_libgen.spec_parser import get_keyword_data

HERE = Path(__file__).parent.resolve()
INIT_TEMPLATE_PATH = HERE / "templates/__init__.jinja"
LIBRARY_TEMPLATE_PATH = HERE / "templates/library.jinja"


def generate(
    openapi_spec: dict[str, Any],
    output_folder: Path,
    library_name: str,
    module_name: str,
) -> str:
    keyword_data = get_keyword_data(openapi_spec=openapi_spec)

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

    return f"Generating {library_name} at {output_folder.resolve().as_posix()}/{module_name}"
