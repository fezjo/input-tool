from test_utils import copy_fixture_tree, run_itool


def test_sample_extracts_io_blocks_into_files(case_dir):
    workdir = copy_fixture_tree("sample_ok", case_dir)

    run_itool(["s", "task.md", "--force-multi"], cwd=workdir)

    assert (workdir / "test" / "00.sample.a.in").read_text() == "3 4\n"
    assert (workdir / "test" / "00.sample.a.out").read_text() == "7\n"


def test_sample_fails_on_mismatched_input_output_blocks(case_dir):
    workdir = copy_fixture_tree("sample_mismatch", case_dir)

    result = run_itool(["s", "task.md"], cwd=workdir, check=False)

    assert result.returncode != 0
    assert "Number of inputs and outputs must be the same." in result.stdout


def test_compile_creates_binaries_for_valid_cpp_sources(case_dir):
    workdir = copy_fixture_tree("progdir", case_dir)

    result = run_itool(["c", "sol-a.cpp", "sol-b.cpp", "-j", "1"], cwd=workdir)

    assert result.returncode == 0
    assert (workdir / "prog" / "sol-a").exists()
    assert (workdir / "prog" / "sol-b").exists()


def test_compile_fails_for_invalid_cpp_source(case_dir):
    workdir = copy_fixture_tree("compile_bad_cpp", case_dir)

    result = run_itool(["c", "sol-bad.cpp", "-j", "1"], cwd=workdir, check=False)

    assert result.returncode != 0
    assert "Compilation failed." in result.stdout
