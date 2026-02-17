from test_utils import (
    copy_fixture_tree,
    filter_out_ansi_escape_codes,
    get_input_files,
    run_itool,
)


def test_sample_extracts_io_blocks_into_files(case_dir):
    workdir = copy_fixture_tree("sample_ok", case_dir)

    run_itool(["s", "task.md", "--force-multi"], cwd=workdir)

    assert sorted(p.name for p in (workdir / "test").iterdir()) == [
        "00.sample.a.in",
        "00.sample.a.out",
    ]
    assert (workdir / "test" / "00.sample.a.in").read_text() == "3 4\n"
    assert (workdir / "test" / "00.sample.a.out").read_text() == "7\n"


def test_sample_fails_on_mismatched_input_output_blocks(case_dir):
    workdir = copy_fixture_tree("sample_mismatch", case_dir)

    result = run_itool(["s", "task.md"], cwd=workdir, check=False)

    assert result.returncode != 0
    assert "Number of inputs and outputs must be the same." in result.stdout


def test_sample_custom_input_output_dirs(case_dir):
    workdir = copy_fixture_tree("sample_ok", case_dir)

    run_itool(
        ["s", "task.md", "--input", "indata", "--output", "outdata", "--force-multi"],
        cwd=workdir,
    )

    assert (workdir / "indata" / "00.sample.a.in").read_text() == "3 4\n"
    assert (workdir / "outdata" / "00.sample.a.out").read_text() == "7\n"


def test_sample_custom_extensions(case_dir):
    workdir = copy_fixture_tree("sample_ok", case_dir)

    run_itool(
        ["s", "task.md", "--inext", "dat", "--outext", "ans", "--force-multi"],
        cwd=workdir,
    )

    assert (workdir / "test" / "00.sample.a.dat").read_text() == "3 4\n"
    assert (workdir / "test" / "00.sample.a.ans").read_text() == "7\n"


def test_sample_custom_batch_name(case_dir):
    workdir = copy_fixture_tree("sample_ok", case_dir)

    run_itool(["s", "task.md", "--batch", "demo", "--force-multi"], cwd=workdir)

    assert (workdir / "test" / "demo.a.in").read_text() == "3 4\n"
    assert (workdir / "test" / "demo.a.out").read_text() == "7\n"


def test_compile_creates_binaries_for_valid_cpp_sources(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    result = run_itool(["c", "sol-a.cpp", "sol-b.cpp"], cwd=workdir)

    assert result.returncode == 0
    assert (workdir / "prog" / "sol-a").exists()
    assert (workdir / "prog" / "sol-b").exists()


def test_compile_fails_for_invalid_cpp_source(case_dir):
    workdir = copy_fixture_tree("compile_bad_cpp", case_dir)

    result = run_itool(["c", "sol-bad.cpp"], cwd=workdir, check=False)

    assert result.returncode != 0
    assert "Compilation failed." in result.stdout


def test_sample_directory_task_autodetects_zadanie_md(case_dir):
    workdir = copy_fixture_tree("sample_dir_task", case_dir)

    run_itool(["s", "statement"], cwd=workdir)

    assert (workdir / "test" / "00.sample.in").read_text() == "1\n"
    assert (workdir / "test" / "00.sample.out").read_text() == "1\n"


def test_compile_progdir_override(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    run_itool(["c", "sol-a.cpp", "--progdir", "build"], cwd=workdir)

    assert (workdir / "build" / "sol-a").exists()


def test_compile_quiet_suppresses_compiler_stdout(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    result = run_itool(["c", "sol-a.cpp", "--progdir", "build", "-q"], cwd=workdir)

    assert result.returncode == 0
    assert "g++" not in result.stdout
    assert (workdir / "build" / "sol-a").exists()


def test_compile_fails_when_progdir_path_is_existing_file(case_dir):
    workdir = copy_fixture_tree("compile_progdir_conflict", case_dir)

    result = run_itool(["c", "sol.cpp", "--progdir", "build"], cwd=workdir, check=False)

    assert result.returncode != 0
    assert "FileExistsError" in result.stdout or "NotADirectoryError" in result.stdout


def test_sample_boring_disables_colors(case_dir):
    workdir = copy_fixture_tree("sample_ok", case_dir)

    result = run_itool(["s", "task.md", "--boring", "--force-multi"], cwd=workdir)

    assert filter_out_ansi_escape_codes(result.stdout) == result.stdout


def test_compile_pythoncmd_override_for_python_targets(case_dir):
    workdir = copy_fixture_tree("tester_pythoncmd", case_dir)

    result = run_itool(
        ["c", "sol.py", "--pythoncmd", "definitely_missing_python"], cwd=workdir
    )

    assert result.returncode == 0
    assert "Python interpreter 'definitely_missing_python' not found" in result.stdout


def test_compile_boring_disables_colors(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    result = run_itool(["c", "sol-a.cpp", "--boring"], cwd=workdir)

    assert result.returncode == 0
    assert filter_out_ansi_escape_codes(result.stdout) == result.stdout
