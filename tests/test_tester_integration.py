from test_utils import (
    copy_fixture_tree,
    filter_out_ansi_escape_codes,
    normalize_results_for_assertions,
    parse_statistics,
    run_itool,
    run_itool_json,
)


def test_timelimit_language_matrix_statuses(case_dir):
    workdir = copy_fixture_tree("timelimits", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir)

    _result, data = run_itool_json(["t", ".", "-t", "1,cpp=0.1"], cwd=workdir)
    normalized = normalize_results_for_assertions(data)

    assert {row["name"]: row["result"] for row in normalized} == {
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


def test_best_only_selects_single_solution(case_dir):
    workdir = copy_fixture_tree("timelimits", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir)

    _result, data = run_itool_json(["t", ".", "--best-only", "-t", "0"], cwd=workdir)
    assert len(data) == 1
    assert data[0]["name"] == "sol.cpp"


def test_side_by_side_diff_and_statuses(case_dir):
    workdir = copy_fixture_tree("sidebyside", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir)

    result, data = run_itool_json(
        ["t", "-FD", "--no-sort", "sol-a.py", "sol-b.py"], cwd=workdir
    )
    out = filter_out_ansi_escape_codes(result.stdout)

    assert {row["name"]: row["result"] for row in data} == {
        "sol-a.py": "OK",
        "sol-b.py": "WA",
    }

    expected_lines = [
        "1 2 3 4 5 6 7 8 9 10                    1 2 3 4 5 6 7 8 9 10",
        "11 12 13 14 15 16 17 18 19 20         | 12 12 13 14 15 16 17 18 19 20",
        "...",
        "81 82 83 84 85 86 87 88 89 90         | 81 82 83 84 85 86 87 89 89 90",
        "91 92 93 94 95 96 97 98 99 100        <",
    ]
    normalized_output = [" ".join(line.split()) for line in out.splitlines()]
    normalized_expected = [" ".join(line.split()) for line in expected_lines]

    offset = 8
    got = normalized_output[-len(normalized_expected) - offset : -offset]
    assert got == normalized_expected


def test_statistics_table_shape(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir)

    result = run_itool(["t", "sol-a.cpp", "./sol-b.cpp", "cdir/sol-c.cpp"], cwd=workdir)
    rows = parse_statistics(result.stdout)

    assert "| Solution" in filter_out_ansi_escape_codes(result.stdout)
    assert len(rows) == 3
    assert all(status == "OK" for *_prefix, status, _batches in rows)


def test_default_fail_skip_skips_remaining_tests_in_batch(case_dir):
    workdir = copy_fixture_tree("failskip", case_dir)

    _result, data = run_itool_json(
        ["t", "sol-fast.py", "sol-slow.py", "-t", "0.05"], cwd=workdir
    )
    by_name = {row["name"]: row for row in data}

    slow = by_name["sol-slow.py"]
    assert slow["result"] == "TLE"
    assert len(slow["times"]["1"]) == 1
    assert len(slow["times"]["2"]) == 1


def test_no_fail_skip_runs_remaining_tests_in_batch(case_dir):
    workdir = copy_fixture_tree("failskip", case_dir)

    _result, data = run_itool_json(
        ["t", "sol-fast.py", "sol-slow.py", "-t", "0.05", "-F"], cwd=workdir
    )
    by_name = {row["name"]: row for row in data}

    slow = by_name["sol-slow.py"]
    assert slow["result"] == "TLE"
    assert len(slow["times"]["1"]) == 2
    assert len(slow["times"]["2"]) == 1


def test_outputs_are_reused_unless_reset_requested(case_dir):
    workdir = copy_fixture_tree("recompute", case_dir)

    first = run_itool(["t", "sol-a.py", "sol-b.py"], cwd=workdir)
    second = run_itool(["t", "sol-a.py", "sol-b.py"], cwd=workdir)
    third = run_itool(["t", "sol-a.py", "sol-b.py", "-R"], cwd=workdir)

    first_text = filter_out_ansi_escape_codes(first.stdout)
    second_text = filter_out_ansi_escape_codes(second.stdout)
    third_text = filter_out_ansi_escape_codes(third.stdout)

    assert "will be created now (doesn't exist)" in first_text
    assert "will be created now" not in second_text
    assert "will be created now (recompute)" in third_text


def test_tester_fails_on_missing_input_directory(case_dir):
    workdir = copy_fixture_tree("missing_input", case_dir)

    result = run_itool(
        ["t", "sol.py", "--input", "does-not-exist"], cwd=workdir, check=False
    )

    assert result.returncode != 0
    assert "Input directory `does-not-exist` doesn't exist." in result.stdout


def test_tester_fails_on_unsupported_checker_format(case_dir):
    workdir = copy_fixture_tree("unsupported_checker", case_dir)

    result = run_itool(
        ["t", "sol-a.py", "sol-b.py", "-d", "mychecker.py", "-t", "0"],
        cwd=workdir,
        check=False,
    )

    assert result.returncode != 0
    assert "Unsupported checker mychecker.py" in result.stdout


def test_validator_reports_valid_status_when_inputs_pass(case_dir):
    workdir = copy_fixture_tree("validator_ok", case_dir)

    _result, data = run_itool_json(
        ["t", "val-positive.py", "sol-copy.py", "-t", "0"], cwd=workdir
    )
    by_name = {row["name"]: row["result"] for row in data}

    assert by_name == {"val-positive.py": "VALID", "sol-copy.py": "OK"}


def test_validator_reports_exc_when_input_fails_validation(case_dir):
    workdir = copy_fixture_tree("validator_fail", case_dir)

    _result, data = run_itool_json(
        ["t", "val-positive.py", "sol-copy.py", "-t", "0"], cwd=workdir
    )
    by_name = {row["name"]: row["result"] for row in data}

    assert by_name == {"val-positive.py": "EXC", "sol-copy.py": "OK"}


def test_json_normalized_snapshot_contract(case_dir):
    workdir = copy_fixture_tree("batch_letters", case_dir)

    _result, data = run_itool_json(["t", "sol.py", "-t", "0"], cwd=workdir)
    normalized = normalize_results_for_assertions(data)

    assert normalized == [
        {
            "name": "sol.py",
            "points": "1",
            "result": "OK",
            "batchresults": {"00.sample": "OK", "1": "OK"},
            "failedbatches": [],
        }
    ]
