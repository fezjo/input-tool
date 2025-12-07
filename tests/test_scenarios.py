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
def test_progdir(setup_directory: None) -> None:
    """
    test if solutions compile into progdir
    TODO test if recompilation is skipped
    """
    result_gen = run("input-generator . -g cat")
    print(result_gen.stdout.decode("utf-8"))

    result_test = run("input-tester sol-a.cpp ./sol-b.cpp cdir/sol-c.cpp")
    print(result_test.stdout.decode("utf-8"))

    assert sorted(os.listdir("prog")) == ["sol-a", "sol-b", "sol-c"]

    statistics = parse_statistics(result_test.stdout.decode("utf-8"))
    assert len(statistics) == 3
    assert all(map(lambda row: row[4] == "OK", statistics))


@pytest.mark.parametrize("path", ["timelimits"])
def test_timelimits(setup_directory: None) -> None:
    """test if timelimits, warntimelimits and language limits are respected"""
    result_gen = run("input-generator . -g cat")
    print(result_gen.stdout.decode("utf-8"))

    result_test = run("input-tester . -t '1,cpp=0.1'")
    print(result_test.stdout.decode("utf-8"))

    statistics = parse_statistics(result_test.stdout.decode("utf-8"))
    assert {row[0]: row[4] for row in statistics} == {
        "sol.cpp": "OK",
        "sol-0.7.cpp": "tOK",
        "sol-1.0.cpp": "TLE",
        "sol-1.py": "OK",
        "sol-2.py": "OK",
        "sol-3.py": "tOK",
        "sol-4.py": "tOK",
        "sol-5.py": "tOK",
        "sol-10.py": "TLE",
    }


@pytest.mark.parametrize("path", ["sidebyside"])
def test_sidebyside(setup_directory: None) -> None:
    """test if diff is displayed correctly"""
    result_gen = run("input-generator . -g cat")
    print(result_gen.stdout.decode("utf-8"))

    result_gen_out = run("input-tester sol-a.py")
    print(result_gen_out.stdout.decode("utf-8"))

    result_test = run("input-tester -FD sol-b.py")
    print(result_test.stdout.decode("utf-8"))

    def normalize_whitespace(text: str) -> list[str]:
        return list(map(lambda s: " ".join(s.split()), text.splitlines()))

    # TODO check that OK doesn't display diff

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
    end_offset = 8
    last_diff_lines_real = result_lines[
        -len(last_diff_lines_expected) - end_offset : -end_offset
    ]
    assert last_diff_lines_real == last_diff_lines_expected


@pytest.mark.parametrize("path", ["languages"])
def test_progdir(setup_directory: None) -> None:
    """
    test if supported languages work
    """
    result_gen = run("input-generator .")
    print(result_gen.stdout.decode("utf-8"))

    # java takes time to start
    result_test = run("input-tester sols/")
    print(result_test.stdout.decode("utf-8"))

    statistics = parse_statistics(result_test.stdout.decode("utf-8"))
    assert len(statistics) == 6
    assert all(map(lambda row: row[4] == "OK" or row[4] == "tOK", statistics))


@pytest.mark.skip(reason="TODO")
@pytest.mark.parametrize("path", ["nameconflict"])
def test_nameconflict(setup_directory: None) -> None:
    """TODO test if name conflict is detected and how it is resolved"""
    pass


@pytest.mark.skip(reason="TODO")
@pytest.mark.parametrize("path", ["allcomponents"])
def test_allcomponents(setup_directory: None) -> None:
    """TODO test if a typical usecase with all components:
    - input-sample
    - compiled input-generator
    - input-tester
        - compiled and interpreted solutions
            - OK, tOK, WA, TLE, EXC
        - validator
        - checker
    """
    pass


@pytest.mark.skip(reason="TODO")
@pytest.mark.parametrize("path", ["idf"])
def test_idf(setup_directory: None) -> None:
    """TODO test if various idf options work:
    - comments `#`
    - custom variables `$`
    - ignore special characters `~`
    - multiline strings `\\`
    - {id}, {batch}, {class}, {name}
    - random {rand}
    - double braces {{text}}
    - multiple generators {gen}
    - out of order batches
    """
    pass


@pytest.mark.skip(reason="TODO")
@pytest.mark.parametrize("path", ["parallel"])
def test_parallel(setup_directory: None) -> None:
    """TODO test if parallelization work - compare speedups"""
    # ! be sure to take into account the time of compilation
    pass


@pytest.mark.skip(reason="TODO")
@pytest.mark.parametrize("path", ["slowgenerator"])
def test_slowgenerator(setup_directory: None) -> None:
    """TODO test if parallel output generation waits for slow model solution"""
    pass


@pytest.mark.skip(reason="TODO")
@pytest.mark.parametrize("path", ["bigmess"])
def test_bigmess(setup_directory: None) -> None:
    """TODO test if a big mess of inputs, solutions and threads works"""
    pass
