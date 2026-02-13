from test_utils import copy_fixture_tree, run_itool


def test_generate_custom_input_dir_and_extension(case_dir):
    workdir = copy_fixture_tree("generate_basic", case_dir)

    run_itool(
        ["g", ".", "-g", "cat", "--input", "cases", "--inext", "dat", "-j", "1"],
        cwd=workdir,
    )

    assert sorted(p.name for p in (workdir / "cases").glob("*.dat")) == [
        "1.a.dat",
        "1.b.dat",
    ]
    assert (workdir / "cases" / "1.a.dat").read_text() == "10\n"
    assert (workdir / "cases" / "1.b.dat").read_text() == "20\n"


def test_generate_keep_inputs_preserves_existing_files(case_dir):
    workdir = copy_fixture_tree("generate_keep_inputs", case_dir)

    run_itool(
        ["g", ".", "-g", "cat", "--input", "test", "--keep-inputs", "-j", "1"],
        cwd=workdir,
    )

    assert (workdir / "test" / "9.z.in").exists()
    assert (workdir / "test" / "9.z.in").read_text() == "legacy\n"
    assert (workdir / "test" / "1.in").exists()
    assert (workdir / "test" / "1.in").read_text() == "30\n"


def test_generate_no_compile_requires_executable_generator(case_dir):
    workdir = copy_fixture_tree("generate_cpp", case_dir)

    result = run_itool(
        ["g", ".", "-g", "gen.cpp", "--no-compile", "-j", "1"], cwd=workdir, check=False
    )

    assert "Generator encountered an error" in result.stdout
    assert result.returncode == 0
    assert not (workdir / "test" / "1.a.in").exists()
    assert not (workdir / "test" / "1.b.in").exists()


def test_generate_execute_runs_generator_as_command(case_dir):
    workdir = copy_fixture_tree("generate_basic", case_dir)

    run_itool(["g", ".", "-g", "cat", "--execute", "-j", "1"], cwd=workdir)

    assert sorted(p.name for p in (workdir / "test").glob("*.in")) == [
        "1.a.in",
        "1.b.in",
    ]
    assert (workdir / "test" / "1.a.in").read_text() == "10\n"
    assert (workdir / "test" / "1.b.in").read_text() == "20\n"


def test_generate_execute_nonexistent_generator_reports_error(case_dir):
    workdir = copy_fixture_tree("generate_basic", case_dir)

    result = run_itool(
        ["g", ".", "-g", "definitely_missing_gen", "--execute", "-j", "1"],
        cwd=workdir,
        check=False,
    )

    assert result.returncode == 0
    assert "Generator encountered an error" in result.stdout
    assert sorted(p.name for p in (workdir / "test").glob("*.in")) == [
        "1.a.in",
        "1.b.in",
    ]
    assert (workdir / "test" / "1.a.in").read_text() == ""
    assert (workdir / "test" / "1.b.in").read_text() == ""


def test_generate_pythoncmd_override_is_used(case_dir):
    workdir = copy_fixture_tree("generate_py", case_dir)

    result = run_itool(
        [
            "g",
            ".",
            "-g",
            "gen.py",
            "--pythoncmd",
            "definitely_missing_python",
            "-j",
            "1",
        ],
        cwd=workdir,
    )

    assert "Python interpreter 'definitely_missing_python' not found" in result.stdout
    assert (workdir / "test" / "1.in").exists()
    assert (workdir / "test" / "1.in").read_text() == "4\n"


def test_generate_progdir_override_compiles_to_custom_dir(case_dir):
    workdir = copy_fixture_tree("generate_cpp", case_dir)

    run_itool(["g", ".", "-g", "gen.cpp", "--progdir", "gprog", "-j", "1"], cwd=workdir)

    assert (workdir / "gprog" / "gen").exists()
    assert not (workdir / "prog" / "gen").exists()
    assert (workdir / "test" / "1.in").read_text() == "3\n"


def test_generate_clear_bin_removes_generator_binaries(case_dir):
    workdir = copy_fixture_tree("generate_cpp", case_dir)

    run_itool(
        ["g", ".", "-g", "gen.cpp", "--progdir", "gprog", "--clear-bin", "-j", "1"],
        cwd=workdir,
    )

    assert not (workdir / "gprog").exists()
    assert (workdir / "test" / "1.in").read_text() == "3\n"
