from test_utils import copy_fixture_tree, run_itool, run_itool_json


def test_keep_temp_preserves_temp_files(case_dir):
    workdir = copy_fixture_tree("recompute", case_dir)

    run_itool(["t", "sol-a.py", "sol-b.py", "-j", "1", "--keep-temp"], cwd=workdir)

    temp_files = sorted((workdir / "test").glob("*.temp"))
    assert temp_files


def test_default_temp_cleanup_removes_temp_files(case_dir):
    workdir = copy_fixture_tree("recompute", case_dir)

    run_itool(["t", "sol-a.py", "sol-b.py", "-j", "1"], cwd=workdir)

    temp_files = sorted((workdir / "test").glob("*.temp"))
    assert not temp_files


def test_no_statistics_hides_summary_table(case_dir):
    workdir = copy_fixture_tree("recompute", case_dir)

    result = run_itool(
        ["t", "sol-a.py", "sol-b.py", "-j", "1", "--no-statistics"],
        cwd=workdir,
    )

    assert "| Solution" not in result.stdout


def test_checker_is_auto_detected_without_diff_flag(case_dir):
    workdir = copy_fixture_tree("checker_approx", case_dir)

    _result, data = run_itool_json(["t", ".", "-F", "-j", "1", "-t", "0"], cwd=workdir)
    by_name = {row["name"]: row["result"] for row in data}

    assert by_name == {
        "sol-ref.py": "OK",
        "sol-close.py": "OK",
        "sol-far.py": "WA",
    }


def test_tester_fails_when_multiple_checkers_found(case_dir):
    workdir = copy_fixture_tree("checker_multiple", case_dir)

    result = run_itool(["t", ".", "-j", "1", "-t", "0"], cwd=workdir, check=False)

    assert result.returncode != 0
    assert "More than one checker found" in result.stdout
