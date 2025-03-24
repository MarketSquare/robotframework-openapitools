# pylint: disable=missing-function-docstring, unused-argument
import os
import pathlib
import subprocess
from importlib.metadata import version

from invoke.context import Context
from invoke.tasks import task

ROOT = pathlib.Path(__file__).parent.resolve().as_posix()
VERSION = version("robotframework-openapitools")


@task
def start_api(context: Context) -> None:
    cmd = [
        "python",
        "-m",
        "uvicorn",
        "testserver:app",
        f"--app-dir {ROOT}/tests/server",
        "--host 0.0.0.0",
        "--port 8000",
        "--reload",
        f"--reload-dir {ROOT}/tests/server",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)


@task
def libgen(context: Context) -> None:
    env = os.environ.copy()
    env["USE_SUMMARY_AS_KEYWORD_NAME"] = "True"
    cmd = [
        "generate-library",
        "-n",
        "'My Generated Library'",
        "-s",
        f"{ROOT}/tests/files/mismatched_openapi.json",
        "-d",
        f"{ROOT}/tests/generated/",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False, env=env)


@task
def utests(context: Context) -> None:
    cmd = [
        "coverage",
        "run",
        "-m",
        "unittest",
        "discover ",
        f"{ROOT}/tests/driver/unittests",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)

    cmd = [
        "coverage",
        "run",
        "-m",
        "unittest",
        "discover ",
        f"{ROOT}/tests/libcore/unittests",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)


@task(libgen)
def atests(context: Context) -> None:
    cmd = [
        "coverage",
        "run",
        "-m",
        "robot",
        f"--pythonpath={ROOT}/tests/generated",
        f"--argumentfile={ROOT}/tests/rf_cli.args",
        f"--variable=root:{ROOT}",
        f"--outputdir={ROOT}/tests/logs",
        "--loglevel=TRACE:DEBUG",
        "--exclude=roboswag",
        f"{ROOT}/tests",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)


@task(utests, atests)
def tests(context: Context) -> None:
    subprocess.run("coverage combine", shell=True, check=False)
    subprocess.run("coverage report", shell=True, check=False)
    subprocess.run("coverage html", shell=True, check=False)


@task
def type_check(context: Context) -> None:
    subprocess.run(f"mypy {ROOT}/src", shell=True, check=False)
    subprocess.run(f"pyright {ROOT}/src", shell=True, check=False)
    subprocess.run(
        f"robotcode analyze code {ROOT}/tests/driver {ROOT}/tests/libcore",
        shell=True,
        check=False,
    )


@task
def lint(context: Context) -> None:
    subprocess.run(f"ruff check {ROOT}/src/OpenApiDriver", shell=True, check=False)
    subprocess.run(f"ruff check {ROOT}/src/OpenApiLibCore", shell=True, check=False)
    subprocess.run(f"pylint {ROOT}/src/OpenApiDriver", shell=True, check=False)
    subprocess.run(f"pylint {ROOT}/src/OpenApiLibCore", shell=True, check=False)
    # subprocess.run(f"pylint {ROOT}/src/roboswag", shell=True, check=False)
    subprocess.run(f"robocop {ROOT}/tests", shell=True, check=False)


@task
def format_code(context: Context) -> None:
    subprocess.run("ruff check --select I --fix", shell=True, check=False)
    subprocess.run("ruff format", shell=True, check=False)
    subprocess.run(f"robotidy {ROOT}/tests", shell=True, check=False)


@task
def libdoc(context: Context) -> None:
    json_file = f"{ROOT}/tests/files/petstore_openapi.json"
    source = f"OpenApiLibCore::{json_file}"
    target = f"{ROOT}/docs/openapi_libcore.html"
    cmd = [
        "python",
        "-m",
        "robot.libdoc",
        f"-v {VERSION}",
        source,
        target,
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)

    json_file = f"{ROOT}/tests/files/petstore_openapi.json"
    source = f"OpenApiDriver.openapidriver.DocumentationGenerator::{json_file}"
    target = f"{ROOT}/docs/openapidriver.html"
    cmd = [
        "python",
        "-m",
        "robot.libdoc",
        "-n OpenApiDriver",
        f"-v {VERSION}",
        source,
        target,
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)


@task
def libspec(context: Context) -> None:
    json_file = f"{ROOT}/tests/files/petstore_openapi.json"
    source = f"OpenApiLibCore::{json_file}"
    target = f"{ROOT}/src/OpenApiLibCore/openapi_libcore.libspec"
    cmd = [
        "python",
        "-m",
        "robot.libdoc",
        f"-v {VERSION}",
        source,
        target,
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)

    json_file = f"{ROOT}/tests/files/petstore_openapi.json"
    source = f"OpenApiDriver.openapidriver.DocumentationGenerator::{json_file}"
    target = f"{ROOT}/src/OpenApiDriver/openapidriver.libspec"
    cmd = [
        "python",
        "-m",
        "robot.libdoc",
        "-n OpenApiDriver",
        f"-v {VERSION}",
        source,
        target,
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)


@task
def readme(context: Context) -> None:
    front_matter = """---\n---\n"""


#     with open(f"{ROOT}/docs/README.md", "w", encoding="utf-8") as readme_file:
#         doc_string = openapi_libcore.__doc__
# readme_file.write(front_matter)
# readme_file.write(str(doc_string).replace("\\", "\\\\").replace("\\\\*", "\\*"))


@task(format_code, libdoc, libspec, readme)
def build(context: Context) -> None:
    subprocess.run("poetry build", shell=True, check=False)
