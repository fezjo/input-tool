# © 2023 fezjo
import os
import re
import shutil
import subprocess
from typing import Iterator

import pytest

text = """
Compiling: cd prog; make VPATH='../..' CXXFLAGS="-O2 -g -std=c++20 $CXXFLAGS" sol-a
make: 'sol-a' is up to date.
Compiling: cd prog; make VPATH='../..' CXXFLAGS="-O2 -g -std=c++20 $CXXFLAGS" sol-b
make: 'sol-b' is up to date.
----- Run commands -----
Program sol-a.cpp   is ran as `./prog/sol-a`
Program sol-b.cpp   is ran as `./prog/sol-b`
------------------------
1.a.in >
    sol-a.cpp       5ms OK
    sol-b.cpp       4ms OK
1.b.in >
    sol-a.cpp       5ms OK
    sol-b.cpp       5ms OK
1.c.in >
    sol-a.cpp       5ms OK
    sol-b.cpp       6ms OK
2.a.in >
    sol-a.cpp       5ms OK
    sol-b.cpp       5ms OK
2.b.in >
    sol-a.cpp       3ms OK
    sol-b.cpp       3ms OK
3.a.in >
    sol-a.cpp       3ms OK
    sol-b.cpp       4ms OK
3.b.in >
    sol-a.cpp       3ms OK
    sol-b.cpp       3ms OK
3.c.in >
    sol-a.cpp       3ms OK
    sol-b.cpp       3ms OK

| Solution  | Max time | Times sum | Pt   3 | Status | Batches |
|-----------|----------|-----------|--------|--------|---------|
| sol-a.cpp |        5 |        32 |      3 | OK     | OOO     |
| sol-b.cpp |        6 |        33 |      3 | OK     | OOO     |

"""


def filter_out_ansi_escape_codes(text: str) -> str:
    # https://stackoverflow.com/a/14693789
    return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)


def line_to_stat(line: str) -> tuple[str, int, int, str, str]:
    """
    | sol-a.cpp |        5 |        32 |      3 | OK     | OOO     |
    """
    items = [item.strip() for item in line.split("|")[1:-1]]
    return (items[0], int(items[1]), int(items[2]), items[3], items[4], items[5])


def parse_statistics(output: str) -> list[tuple[str, int, int, str, str]]:
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


def clean() -> None:
    shutil.rmtree("test", ignore_errors=True)


@pytest.fixture
def setup_directory(
    request: pytest.FixtureRequest, path: str, cleanup: bool = True
) -> Iterator[None]:
    # change to directory of the test
    os.chdir(os.path.join(os.path.dirname(request.path), path))
    if cleanup:
        clean()
    yield
    os.chdir(request.config.invocation_params.dir)


def run(command: str, out_err_merge: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if out_err_merge else subprocess.PIPE,
    )
    return result


if __name__ == "__main__":
    print(parse_statistics(text))
