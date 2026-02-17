import time
from pathlib import Path

import pytest
from test_utils import (
    copy_fixture_tree,
    filter_out_ansi_escape_codes,
    parse_statistics,
    run_itool,
    run_itool_json,
)


def _measure_tester_wall_time(workdir: Path, threads: int, timeout: float) -> float:
    start = time.monotonic()
    run_itool(["t", ".", "-R", "-q", "-t", str(timeout)], cwd=workdir, threads=threads)
    return time.monotonic() - start


def test_tester_wtime_marks_t_statuses(case_dir):
    workdir = copy_fixture_tree("timelimits", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir, threads=None)

    sols = ["sol.cpp", "sol-1.0.cpp", "sol-1.py"]
    _result, data = run_itool_json(
        ["t", *sols, "-t", "2", "--wtime", "0.0001"], cwd=workdir
    )

    assert len(data) == len(sols)
    assert {row["name"] for row in data} == set(sols)
    assert all(row["result"].startswith("t") for row in data)


def test_tester_wtime_high_threshold_produces_no_t_statuses(case_dir):
    workdir = copy_fixture_tree("timelimits", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir, threads=None)

    sols = ["sol.cpp", "sol-1.0.cpp", "sol-1.py"]
    _result, data = run_itool_json(
        ["t", *sols, "-t", "1,cpp=0.1", "--wtime", "100"], cwd=workdir
    )

    assert len(data) == len(sols)
    assert {row["name"] for row in data} == set(sols)
    assert all(not row["result"].startswith("t") for row in data)


def test_tester_memorylimit_triggers_failure(case_dir):
    workdir = copy_fixture_tree("tester_memory", case_dir)

    _result, data = run_itool_json(
        ["t", ".", "-m", "100", "-t", "0", "-q"], cwd=workdir
    )
    assert len(data) == 2
    assert {row["name"] for row in data} == {"sol-mem.cpp", "sol-mem.py"}
    batch_results = [
        "".join(row["batchresults"][str(i)][0] for row in data) for i in range(1, 6)
    ]
    print(batch_results)
    assert batch_results[0] == "OO"  # first test is very easy
    assert "O" in batch_results[1]  # python has some issues, but C++ should be fine
    assert "E" in batch_results[2]  # at least one should fail the stack limit
    assert "E" in batch_results[3]  # at least one should fail the heap limit
    assert batch_results[4] == "EE"  # test allocates a lot of memory, both should fail


def test_tester_no_compile_requires_prebuilt_binary(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    _result, data = run_itool_json(
        ["t", "sol-a.cpp", "--no-compile", "-t", "0"], cwd=workdir
    )

    assert len(data) == 1
    assert data[0]["name"] == "sol-a.cpp"
    assert data[0]["result"] == "EXC"


def test_tester_execute_treats_program_as_shell_command(case_dir):
    workdir = copy_fixture_tree("tester_execute", case_dir)

    _result, data = run_itool_json(["t", "--execute", "cat", "-t", "0"], cwd=workdir)

    assert len(data) == 1
    assert data[0]["name"] == "cat"
    assert data[0]["result"] == "OK"
    assert (workdir / "test" / "1.a.out").read_text() == "5\n"


def test_tester_execute_nonexistent_command_results_exc(case_dir):
    workdir = copy_fixture_tree("tester_execute", case_dir)

    _result, data = run_itool_json(
        ["t", "--execute", "definitely_missing_cmd", "-t", "0"], cwd=workdir
    )

    assert len(data) == 1
    assert data[0]["name"] == "definitely_missing_cmd"
    assert data[0]["result"] == "EXC"


def test_tester_pythoncmd_override_is_used(case_dir):
    workdir = copy_fixture_tree("tester_pythoncmd", case_dir)

    result, data = run_itool_json(
        ["t", "sol.py", "--pythoncmd", "definitely_missing_python", "-t", "0"],
        cwd=workdir,
    )

    assert "Python interpreter 'definitely_missing_python' not found" in result.stdout
    assert len(data) == 1
    assert data[0]["name"] == "sol.py"
    assert data[0]["result"] == "OK"


def test_tester_custom_output_dir_and_extensions(case_dir):
    workdir = copy_fixture_tree("tester_custom_io", case_dir)

    _result, data = run_itool_json(
        ["t", "sol.py", "-t", "0"]
        + ["--input", "input_data", "--output", "output_data"]
        + ["--inext", "dat", "--outext", "ans"],
        cwd=workdir,
    )

    assert (workdir / "output_data" / "1.a.ans").exists()
    assert (workdir / "output_data" / "1.b.ans").exists()
    assert (workdir / "output_data" / "1.a.ans").read_text() == "11\n"
    assert (workdir / "output_data" / "1.b.ans").read_text() == "22\n"
    assert not (workdir / "test" / "1.a.out").exists()
    assert data[0]["result"] == "OK"


def test_tester_progdir_override_compiles_to_custom_dir(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    _result, data = run_itool_json(
        ["t", "sol-a.cpp", "--progdir", "build", "-t", "0"], cwd=workdir
    )

    assert (workdir / "build" / "sol-a").exists()
    assert len(data) == 1
    assert data[0]["name"] == "sol-a.cpp"
    assert data[0]["result"] == "OK"


def test_statistics_table_header_contract(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir, threads=None)

    result = run_itool(["t", "sol-a.cpp", "./sol-b.cpp", "cdir/sol-c.cpp"], cwd=workdir)
    text = filter_out_ansi_escape_codes(result.stdout)

    header_line = next(
        line for line in text.splitlines() if line.startswith("| Solution")
    )
    separator_line = next(
        line for line in text.splitlines() if line.startswith("|-----------")
    )

    expected_cols = ["Solution", "Max time", "Times sum", "Pt", "Status", "Batches"]
    for token in expected_cols:
        assert token in header_line
    pieces = [p.strip() for p in header_line.split("|")[1:-1]]
    assert len(pieces) == 6
    assert pieces[0] == "Solution"
    assert pieces[1] == "Max time"
    assert pieces[2] == "Times sum"
    assert pieces[4] == "Status"
    assert pieces[5] == "Batches"
    assert separator_line.count("|") == header_line.count("|")


def test_statistics_table_row_alignment_contract(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir, threads=None)

    result = run_itool(["t", "sol-a.cpp", "./sol-b.cpp", "cdir/sol-c.cpp"], cwd=workdir)
    lines = filter_out_ansi_escape_codes(result.stdout).splitlines()
    row_lines = [line for line in lines if line.startswith("| sol")]

    assert row_lines
    for line in row_lines:
        assert line.endswith("|")
        assert len([x for x in line.split("|")[1:-1]]) == 6


def test_statistics_table_batch_letters_contract(case_dir):
    workdir = copy_fixture_tree("batch_letters", case_dir)

    result = run_itool(["t", "sol.py", "-t", "0"], cwd=workdir)
    text = filter_out_ansi_escape_codes(result.stdout)
    rows = parse_statistics(text)

    assert "| sol.py" in text
    assert "| oO" in text
    assert len(rows) == 1
    assert rows[0][0] == "sol.py"
    assert rows[0][5] == "oO"


def test_tester_rustime_prints_rus_columns(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    result = run_itool(["t", "sol-a.cpp", "--rustime", "-t", "0"], cwd=workdir)

    assert result.returncode == 0
    assert "[" in result.stdout
    assert "+" in result.stdout
    assert "]" in result.stdout


def test_tester_ioram_executes_in_ramdisk(case_dir):
    if not Path("/dev/shm").exists():
        pytest.xfail("/dev/shm is not available in this environment.")

    workdir = copy_fixture_tree("progdir", case_dir)

    result = run_itool(["t", "sol-a.cpp", "--ioram", "-t", "0"], cwd=workdir)

    assert result.returncode == 0
    assert "Using /dev/shm/input_tool/" in result.stdout


@pytest.mark.timing_sensitive
def test_parallel_testing_linear_fixture_is_faster_with_more_threads(case_dir):
    workdir = copy_fixture_tree("parallel_finish_order_linear", case_dir)
    run_itool(["g", ".", "-g", "cat", "-q"], cwd=workdir, threads=None)

    single_thread = _measure_tester_wall_time(workdir, threads=1, timeout=0.2)
    three_threads = _measure_tester_wall_time(workdir, threads=3, timeout=0.2)

    assert three_threads < single_thread * 0.5


@pytest.mark.timing_sensitive
def test_parallel_testing_poly_fixture_is_faster_with_more_threads(case_dir):
    workdir = copy_fixture_tree("parallel_finish_order_poly", case_dir)
    run_itool(["g", ".", "-g", "cat", "-q"], cwd=workdir, threads=None)

    single_thread = _measure_tester_wall_time(workdir, threads=1, timeout=0.2)
    three_threads = _measure_tester_wall_time(workdir, threads=3, timeout=0.2)

    assert three_threads < single_thread * 0.5


@pytest.mark.timing_sensitive
def test_parallel_testing_takes_minimal_amount_of_time(case_dir):
    """
    The input has 12 batches by 4 testcases each,
    where one program finishes instantly and the other times out after 1 second.
    When ran with 7 threads, the minimum amount of time needed to finish:
    - the fast program is 12*4*(python startup=~15ms) = 720ms
    - the slow program is 2 seconds (we can't TLE on all 12 batches with just 7 threads)
    With clairvoyant scheduling, we could finish in 2 seconds, but with a reasonable scheduling
    we expect to finish under 2.5 seconds.
    """
    workdir = copy_fixture_tree("parallel_finish_order", case_dir)
    run_itool(["g", ".", "-g", "cat", "-q"], cwd=workdir, threads=None)

    assert _measure_tester_wall_time(workdir, threads=7, timeout=1) < 2.7
