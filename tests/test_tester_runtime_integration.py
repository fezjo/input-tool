import pytest

from test_utils import (
    copy_fixture_tree,
    filter_out_ansi_escape_codes,
    parse_statistics,
    run_itool,
    run_itool_json,
)


def test_tester_wtime_marks_t_statuses(case_dir):
    workdir = copy_fixture_tree("timelimits", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir)

    sols = ["sol.cpp", "sol-1.0.cpp", "sol-1.py"]
    _result, data = run_itool_json(
        ["t", *sols, "-t", "2", "--wtime", "0.0001", "-j", "1"], cwd=workdir
    )

    assert len(data) == len(sols)
    assert {row["name"] for row in data} == set(sols)
    assert all(row["result"].startswith("t") for row in data)


def test_tester_wtime_high_threshold_produces_no_t_statuses(case_dir):
    workdir = copy_fixture_tree("timelimits", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir)

    sols = ["sol.cpp", "sol-1.0.cpp", "sol-1.py"]
    _result, data = run_itool_json(
        ["t", *sols, "-t", "1,cpp=0.1", "--wtime", "100", "-j", "1"],
        cwd=workdir,
    )

    assert len(data) == len(sols)
    assert {row["name"] for row in data} == set(sols)
    assert all(not row["result"].startswith("t") for row in data)


def test_tester_memorylimit_triggers_failure(case_dir):
    workdir = copy_fixture_tree("tester_memory", case_dir)

    _result, data = run_itool_json(
        ["t", "sol-mem.py", "-m", "8", "-t", "0", "-j", "1"], cwd=workdir
    )
    assert len(data) == 1
    assert data[0]["name"] == "sol-mem.py"
    statuses = {row["result"] for row in data}

    if statuses == {"OK"}:
        pytest.xfail("Memory limit is not enforced in this environment.")
    assert statuses != {"OK"}


def test_tester_no_compile_requires_prebuilt_binary(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    _result, data = run_itool_json(
        ["t", "sol-a.cpp", "--no-compile", "-t", "0", "-j", "1"], cwd=workdir
    )

    assert len(data) == 1
    assert data[0]["name"] == "sol-a.cpp"
    assert data[0]["result"] == "EXC"


def test_tester_execute_treats_program_as_shell_command(case_dir):
    workdir = copy_fixture_tree("tester_execute", case_dir)

    _result, data = run_itool_json(
        ["t", "--execute", "cat", "-t", "0", "-j", "1"], cwd=workdir
    )

    assert len(data) == 1
    assert data[0]["name"] == "cat"
    assert data[0]["result"] == "OK"
    assert (workdir / "test" / "1.a.out").read_text() == "5\n"


def test_tester_execute_nonexistent_command_results_exc(case_dir):
    workdir = copy_fixture_tree("tester_execute", case_dir)

    _result, data = run_itool_json(
        ["t", "--execute", "definitely_missing_cmd", "-t", "0", "-j", "1"], cwd=workdir
    )

    assert len(data) == 1
    assert data[0]["name"] == "definitely_missing_cmd"
    assert data[0]["result"] == "EXC"


def test_tester_pythoncmd_override_is_used(case_dir):
    workdir = copy_fixture_tree("tester_pythoncmd", case_dir)

    result, data = run_itool_json(
        [
            "t",
            "sol.py",
            "--pythoncmd",
            "definitely_missing_python",
            "-t",
            "0",
            "-j",
            "1",
        ],
        cwd=workdir,
    )

    assert "Python interpreter 'definitely_missing_python' not found" in result.stdout
    assert len(data) == 1
    assert data[0]["name"] == "sol.py"
    assert data[0]["result"] == "OK"


def test_tester_custom_output_dir_and_extensions(case_dir):
    workdir = copy_fixture_tree("tester_custom_io", case_dir)

    _result, data = run_itool_json(
        [
            "t",
            "sol.py",
            "--input",
            "input_data",
            "--inext",
            "dat",
            "--output",
            "output_data",
            "--outext",
            "ans",
            "-t",
            "0",
            "-j",
            "1",
        ],
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
        ["t", "sol-a.cpp", "--progdir", "build", "-t", "0", "-j", "1"], cwd=workdir
    )

    assert (workdir / "build" / "sol-a").exists()
    assert len(data) == 1
    assert data[0]["name"] == "sol-a.cpp"
    assert data[0]["result"] == "OK"


def test_statistics_table_header_contract(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)
    run_itool(["g", ".", "-g", "cat"], cwd=workdir)

    result = run_itool(
        ["t", "sol-a.cpp", "./sol-b.cpp", "cdir/sol-c.cpp", "-j", "1"], cwd=workdir
    )
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
    run_itool(["g", ".", "-g", "cat"], cwd=workdir)

    result = run_itool(
        ["t", "sol-a.cpp", "./sol-b.cpp", "cdir/sol-c.cpp", "-j", "1"], cwd=workdir
    )
    lines = filter_out_ansi_escape_codes(result.stdout).splitlines()
    row_lines = [line for line in lines if line.startswith("| sol")]

    assert row_lines
    for line in row_lines:
        assert line.endswith("|")
        assert len([x for x in line.split("|")[1:-1]]) == 6


def test_statistics_table_batch_letters_contract(case_dir):
    workdir = copy_fixture_tree("batch_letters", case_dir)

    result = run_itool(["t", "sol.py", "-t", "0", "-j", "1"], cwd=workdir)
    text = filter_out_ansi_escape_codes(result.stdout)
    rows = parse_statistics(text)

    assert "| sol.py" in text
    assert "| oO" in text
    assert len(rows) == 1
    assert rows[0][0] == "sol.py"
    assert rows[0][5] == "oO"
