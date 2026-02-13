import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterator

import pytest


def filter_out_ansi_escape_codes(text: str) -> str:
    # https://stackoverflow.com/a/14693789
    return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)


def line_to_stat(line: str) -> tuple[str, int, int, str, str, str]:
    """
    | sol-a.cpp |        5 |        32 |      3 | OK     | OOO     |
    """
    items = [item.strip() for item in line.split("|")[1:-1]]
    return (items[0], int(items[1]), int(items[2]), items[3], items[4], items[5])


def parse_statistics(output: str) -> list[tuple[str, int, int, str, str, str]]:
    """
    <start of file>
    ...

    | Solution  | Max time | Times sum | Pt   3 | Status | Batches |
    |-----------|----------|-----------|--------|--------|---------|
    | sol-a.cpp |        5 |        32 |      3 | OK     | OOO     |
    | sol-b.cpp |        6 |        33 |      3 | OK     | OOO     |
    | val.cpp   |        6 |        16 |  VALID | OK     | VVV     |
    <end of file>

    parse out the table and return it

    [
        ("sol-a.cpp", 5, 32,    "3",  "OK", "OOO"),
        ("sol-b.cpp", 6, 33,    "3",  "OK", "OOO"),
        ("val.cpp",   6, 16, "VALID", "OK", "VVV"),
    ]
    """

    output = filter_out_ansi_escape_codes(output)
    table = re.search(
        r"^(\|\s*Solution[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|.*)",
        output,
        re.MULTILINE | re.DOTALL,
    )
    if table is None:
        return []
    rows = tuple(map(str.strip, table.group(1).splitlines()[2:]))
    return [line_to_stat(row) for row in rows if row.startswith("|")]


def clean(workdir: Path) -> None:
    shutil.rmtree(workdir / "test", ignore_errors=True)


@pytest.fixture
def setup_directory(
    request: pytest.FixtureRequest, path: str, cleanup: bool = True
) -> Iterator[None]:
    # change to directory of the test
    os.chdir(os.path.join(os.path.dirname(request.path), path))
    if cleanup:
        clean(Path.cwd())
    yield
    os.chdir(request.config.invocation_params.dir)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def fixture_path(name: str) -> Path:
    return Path(__file__).resolve().parent / name


@pytest.fixture
def case_dir(tmp_path: Path) -> Iterator[Path]:
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(cwd)


def copy_fixture_tree(name: str, destination: Path) -> Path:
    src = fixture_path(name)
    dst = destination / name
    shutil.copytree(src, dst)
    return dst


def run_itool(
    args: list[str],
    cwd: Path,
    check: bool = True,
    merge_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["uv", "run", "itool", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge_output else subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"Command failed with code {result.returncode}:"
            f"\n$ uv run itool {' '.join(args)}\n{result.stdout}"
        )
    return result


def run_itool_json(
    args: list[str], cwd: Path, json_path: str = "out.json"
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, Any]]]:
    result = run_itool([*args, "--json", json_path], cwd=cwd)
    with open(cwd / json_path) as f:
        data = json.load(f)
    return result, data


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize_json_value(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [_normalize_json_value(v) for v in value]
    return value


def normalize_results_for_assertions(
    data: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = []
    for row in data:
        r = dict(row)
        r.pop("maxtime", None)
        r.pop("sumtime", None)
        r.pop("times", None)
        normalized.append(_normalize_json_value(r))
    return sorted(normalized, key=lambda r: r["name"])
