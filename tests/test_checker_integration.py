from test_utils import copy_fixture_tree, run_itool, run_itool_json


def test_explicit_diff_checker_matches_expected_wa(case_dir):
    workdir = copy_fixture_tree("sidebyside", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir)

    _result, data = run_itool_json(
        ["t", "sol-a.py", "sol-b.py", "-d", "diff", "-F", "--no-sort"], cwd=workdir
    )
    assert len(data) == 2
    by_name = {row["name"]: row["result"] for row in data}

    assert by_name == {"sol-a.py": "OK", "sol-b.py": "WA"}


def test_check_checker_allows_approximate_float_comparisons(case_dir):
    workdir = copy_fixture_tree("checker_approx", case_dir)

    _result, data = run_itool_json(
        ["t", "sol-ref.py", "sol-close.py", "sol-far.py"]
        + ["-d", "check.py", "-F", "-t", "0"],
        cwd=workdir,
    )
    assert len(data) == 3
    by_name = {row["name"]: row["result"] for row in data}

    assert by_name == {"sol-ref.py": "OK", "sol-close.py": "OK", "sol-far.py": "WA"}


def test_check_checker_nonstandard_exit_code_reports_warning_and_marks_wa(case_dir):
    workdir = copy_fixture_tree("checker_badexit", case_dir)

    result, data = run_itool_json(
        ["t", "sol-ref.py", "sol-alt.py", "-d", "check.py", "-F", "-t", "0"],
        cwd=workdir,
    )

    assert len(data) == 2
    by_name = {row["name"]: row["result"] for row in data}
    assert by_name == {"sol-ref.py": "WA", "sol-alt.py": "WA"}
    assert "Checker exited with status" in result.stdout
