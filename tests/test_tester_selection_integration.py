from test_utils import copy_fixture_tree, run_itool_json


def test_default_sort_prefers_better_scored_solution(case_dir):
    workdir = copy_fixture_tree("selection_cases", case_dir)

    _result, data = run_itool_json(
        ["t", "sol-1.py", "sol-100.py", "-t", "0", "-j", "1"],
        cwd=workdir,
    )

    assert len(data) == 2
    assert [row["name"] for row in data] == ["sol-100.py", "sol-1.py"]
    assert [row["result"] for row in data] == ["OK", "OK"]


def test_no_sort_preserves_user_program_order(case_dir):
    workdir = copy_fixture_tree("selection_cases", case_dir)

    _result, data = run_itool_json(
        ["t", "--no-sort", "sol-1.py", "sol-100.py", "-t", "0", "-j", "1"],
        cwd=workdir,
    )

    assert len(data) == 2
    assert [row["name"] for row in data] == ["sol-1.py", "sol-100.py"]
    assert [row["result"] for row in data] == ["OK", "OK"]


def test_default_deduplicates_same_program_argument(case_dir):
    workdir = copy_fixture_tree("selection_cases", case_dir)

    _result, data = run_itool_json(
        ["t", "sol-100.py", "sol-100.py", "-t", "0", "-j", "1"],
        cwd=workdir,
    )

    assert len(data) == 1
    assert data[0]["name"] == "sol-100.py"
    assert data[0]["result"] == "OK"


def test_dupprog_keeps_duplicate_program_argument(case_dir):
    workdir = copy_fixture_tree("selection_cases", case_dir)

    _result, data = run_itool_json(
        ["t", "--dupprog", "sol-100.py", "sol-100.py", "-t", "0", "-j", "1"],
        cwd=workdir,
    )

    assert len(data) == 2
    assert [row["name"] for row in data] == ["sol-100.py", "sol-100.py"]
    assert [row["result"] for row in data] == ["OK", "OK"]


def test_best_only_keeps_validator_and_best_solution(case_dir):
    workdir = copy_fixture_tree("selection_cases", case_dir)

    _result, data = run_itool_json(
        [
            "t",
            "--best-only",
            "val-positive.py",
            "sol-1.py",
            "sol-100.py",
            "-t",
            "0",
            "-j",
            "1",
        ],
        cwd=workdir,
    )

    assert len(data) == 2
    assert [row["name"] for row in data] == ["val-positive.py", "sol-100.py"]
    assert [row["result"] for row in data] == ["VALID", "OK"]
