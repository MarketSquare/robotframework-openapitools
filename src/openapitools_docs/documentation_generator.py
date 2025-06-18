import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from openapitools_docs.docstrings import (
    OPENAPIDRIVER_INIT_DOCSTRING,
    OPENAPIDRIVER_LIBRARY_DOCSTRING,
    OPENAPIDRIVER_MODULE_DOCSTRING,
    OPENAPILIBCORE_INIT_DOCSTRING,
    OPENAPILIBCORE_LIBRARY_DOCSTRING,
    OPENAPILIBCORE_MODULE_DOCSTRING,
)

HERE = Path(__file__).parent.resolve()


def generate(output_folder: Path) -> None:
    output_folder.mkdir(parents=True, exist_ok=True)

    environment = Environment(loader=FileSystemLoader(f"{HERE}/templates/"))

    documentation_template = environment.get_template("documentation.jinja")
    output_file_path = output_folder / "documentation.html"
    documentation_content = documentation_template.render(
        libgen_documentation="To be added",
        driver_documentation=OPENAPIDRIVER_MODULE_DOCSTRING,
        libcore_documentation=OPENAPILIBCORE_MODULE_DOCSTRING,
    )
    with open(output_file_path, mode="w", encoding="utf-8") as html_file:
        html_file.write(documentation_content)


if __name__ == "__main__":  # pragma: no cover
    output_folder = Path(sys.argv[1])
    generate(output_folder=output_folder)
