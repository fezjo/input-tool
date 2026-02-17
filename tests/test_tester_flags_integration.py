from test_utils import copy_fixture_tree, run_itool, run_itool_json


def test_keep_temp_preserves_temp_files(case_dir):
    workdir = copy_fixture_tree("recompute", case_dir)

    run_itool(["t", "sol-a.py", "sol-b.py", "--keep-temp"], cwd=workdir)

    temp_files = sorted((workdir / "test").glob("*.temp"))
    assert temp_files


def test_default_temp_cleanup_removes_temp_files(case_dir):
    workdir = copy_fixture_tree("recompute", case_dir)

    run_itool(["t", "sol-a.py", "sol-b.py"], cwd=workdir)

    temp_files = sorted((workdir / "test").glob("*.temp"))
    assert not temp_files


def test_no_statistics_hides_summary_table(case_dir):
    workdir = copy_fixture_tree("recompute", case_dir)

    result = run_itool(["t", "sol-a.py", "sol-b.py", "--no-statistics"], cwd=workdir)

    assert "| Solution" not in result.stdout


def test_checker_is_auto_detected_without_diff_flag(case_dir):
    workdir = copy_fixture_tree("checker_approx", case_dir)

    _result, data = run_itool_json(["t", ".", "-F", "-t", "0"], cwd=workdir)
    assert len(data) == 3
    by_name = {row["name"]: row["result"] for row in data}

    assert by_name == {"sol-ref.py": "OK", "sol-close.py": "OK", "sol-far.py": "WA"}


def test_tester_fails_when_multiple_checkers_found(case_dir):
    workdir = copy_fixture_tree("checker_multiple", case_dir)

    result = run_itool(["t", ".", "-t", "0"], cwd=workdir, check=False)

    assert result.returncode != 0
    assert "More than one checker found" in result.stdout


def test_tester_clear_bin_removes_compiled_artifacts(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    run_itool(
        ["t", "sol-a.cpp", "--progdir", "build", "--clear-bin", "-t", "0"], cwd=workdir
    )

    assert not (workdir / "build").exists()
