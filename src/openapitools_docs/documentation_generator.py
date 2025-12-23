import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from openapitools_docs.docstrings import (
    ADVANCED_USE_DOCUMENTATION,
    OPENAPIDRIVER_DOCUMENTATION,
    OPENAPILIBCORE_DOCUMENTATION,
    OPENAPILIBGEN_DOCUMENTATION,
)

HERE = Path(__file__).parent.resolve()


def generate(output_folder: Path) -> None:
    output_folder.mkdir(parents=True, exist_ok=True)

    environment = Environment(loader=FileSystemLoader(f"{HERE}/templates/"))

    documentation_template = environment.get_template("documentation.jinja")
    output_file_path = output_folder / "index.html"
    documentation_content = documentation_template.render(
        libgen_documentation=OPENAPILIBGEN_DOCUMENTATION,
        driver_documentation=OPENAPIDRIVER_DOCUMENTATION,
        libcore_documentation=OPENAPILIBCORE_DOCUMENTATION,
        advanced_use_documentation=ADVANCED_USE_DOCUMENTATION,
    )
    with open(output_file_path, mode="w", encoding="UTF-8") as html_file:
        html_file.write(documentation_content)


if __name__ == "__main__":  # pragma: no cover
    output_folder = Path(sys.argv[1])
    generate(output_folder=output_folder)
