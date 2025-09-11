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
    cmd = [
        "coverage",
        "run",
        "-m",
        "openapi_libgen.generator",
        "http://127.0.0.1:8000/openapi.json",
        f"{ROOT}/tests/generated",
        "MyGeneratedLibrary",
        "my_generated_library",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)


@task
def libgen_with_envs(context: Context) -> None:
    env = os.environ.copy()
    env["USE_SUMMARY_AS_KEYWORD_NAME"] = "true"
    env["EXPAND_BODY_ARGUMENTS"] = "true"
    cmd = [
        "coverage",
        "run",
        "-m",
        "openapi_libgen.generator",
        "http://127.0.0.1:8000/openapi.json",
        f"{ROOT}/tests/generated",
        "MyOtherGeneratedLibrary",
        "my_other_generated_library",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False, env=env)


@task
def libgen_edge_cases(context: Context) -> None:
    cmd = [
        "coverage",
        "run",
        "-m",
        "openapi_libgen.generator",
        f"{ROOT}/tests/files/schema_with_parameter_name_duplication.yaml",
        f"{ROOT}/tests/generated",
        "MyGeneratedEdgeCaseLibrary",
        "my_generated_edge_case_library",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)


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

    cmd = [
        "coverage",
        "run",
        "-m",
        "unittest",
        "discover ",
        f"{ROOT}/tests/libgen/unittests",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)


@task(libgen, libgen_with_envs, libgen_edge_cases)
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
    # subprocess.run(
    #     f"robotcode analyze code {ROOT}/tests",
    #     shell=True,
    #     check=False,
    # )


@task
def lint(context: Context) -> None:
    subprocess.run(f"ruff check {ROOT}/src/OpenApiDriver", shell=True, check=False)
    subprocess.run(f"ruff check {ROOT}/src/OpenApiLibCore", shell=True, check=False)
    subprocess.run(f"pylint {ROOT}/src/OpenApiDriver", shell=True, check=False)
    subprocess.run(f"pylint {ROOT}/src/OpenApiLibCore", shell=True, check=False)
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

    env = os.environ.copy()
    env["HIDE_INHERITED_KEYWORDS"] = "true"
    json_file = f"{ROOT}/tests/files/petstore_openapi.json"
    source = f"OpenApiDriver::{json_file}"
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
    subprocess.run(" ".join(cmd), shell=True, check=False, env=env)


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

    env = os.environ.copy()
    env["HIDE_INHERITED_KEYWORDS"] = "true"
    json_file = f"{ROOT}/tests/files/petstore_openapi.json"
    source = f"OpenApiDriver::{json_file}"
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
    subprocess.run(" ".join(cmd), shell=True, check=False, env=env)


@task(libdoc)
def generate_docs(context: Context) -> None:
    cmd = [
        "python",
        "-m",
        "openapitools_docs.documentation_generator",
        f"{ROOT}/docs",
    ]
    subprocess.run(" ".join(cmd), shell=True, check=False)


@task(format_code, libspec, generate_docs)
def build(context: Context) -> None:
    subprocess.run("poetry build", shell=True, check=False)
