import os

import pytest
from test_utils import (
    filter_out_ansi_escape_codes,
    parse_statistics,
    run,
    setup_directory,
)

setup_directory = setup_directory


@pytest.mark.parametrize("path", ["progdir"])
def test_progdir(setup_directory: None):
    result_gen = run("input-generator . -g cat")
    print(result_gen.stdout.decode("utf-8"))

    result_test = run("input-tester sol-a.cpp ./sol-b.cpp cdir/sol-c.cpp")
    print(result_test.stdout.decode("utf-8"))

    assert sorted(os.listdir("test/prog")) == ["sol-a", "sol-b", "sol-c"]

    statistics = parse_statistics(result_test.stdout.decode("utf-8"))
    assert len(statistics) == 3
    assert all(map(lambda row: row[4] == "OK", statistics))


@pytest.mark.parametrize("path", ["timelimits"])
def test_timelimits(setup_directory: None):
    result_gen = run("input-generator . -g cat")
    print(result_gen.stdout.decode("utf-8"))

    result_test = run("input-tester . -t '1,cpp=0.1'")
    print(result_test.stdout.decode("utf-8"))

    statistics = parse_statistics(result_test.stdout.decode("utf-8"))
    assert {row[0]: row[4] for row in statistics} == {
        "sol.cpp": "OK",
        "sol-1.py": "OK",
        "sol-2.py": "OK",
        "sol-3.py": "tOK",
        "sol-4.py": "tOK",
        "sol-5.py": "tOK",
        "sol-10.py": "TLE",
    }


@pytest.mark.parametrize("path", ["sidebyside"])
def test_sidebyside(setup_directory: None):
    result_gen = run("input-generator . -g cat")
    print(result_gen.stdout.decode("utf-8"))

    result_test = run("input-tester -FD sol-a.py sol-b.py")
    print(result_test.stdout.decode("utf-8"))

    def normalize_whitespace(text: str) -> list[str]:
        return list(map(lambda s: " ".join(s.split()), text.splitlines()))

    last_diff_lines_expected = normalize_whitespace(
        """1 2 3 4 5 6 7 8 9 10                    1 2 3 4 5 6 7 8 9 10
11 12 13 14 15 16 17 18 19 20         | 12 12 13 14 15 16 17 18 19 20
...
81 82 83 84 85 86 87 88 89 90         | 81 82 83 84 85 86 87 89 89 90
91 92 93 94 95 96 97 98 99 100        <
"""
    )

    result_text = filter_out_ansi_escape_codes(result_test.stdout.decode("utf-8"))
    result_lines = normalize_whitespace(result_text)
    offset = 6
    last_diff_lines_real = result_lines[
        -len(last_diff_lines_expected) - offset : -offset
    ]
    assert last_diff_lines_real == last_diff_lines_expected
