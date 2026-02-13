from test_utils import copy_fixture_tree, run_itool, run_itool_json


def test_autogenerate_generates_and_tests_best_solution_only(case_dir):
    workdir = copy_fixture_tree("autogenerate_ok", case_dir)

    _result, data = run_itool_json(
        ["ag", ".", ".", "-g", "cat", "-j", "1"],
        cwd=workdir,
    )

    assert (workdir / "test" / "1.a.in").read_text() == "5\n"
    assert (workdir / "test" / "1.b.in").read_text() == "7\n"
    assert (workdir / "test" / "1.a.out").read_text() == "5\n"
    assert (workdir / "test" / "1.b.out").read_text() == "7\n"

    assert len(data) == 1
    assert data[0]["name"] == "sol.py"
    assert data[0]["result"] == "OK"


def test_autogenerate_fails_with_multiple_idf_candidates(case_dir):
    workdir = copy_fixture_tree("autogenerate_multi_idf", case_dir)

    result = run_itool(["ag", ".", ".", "-g", "cat"], cwd=workdir, check=False)

    assert result.returncode != 0
    assert "Found 2 idf files" in result.stdout


def test_autogenerate_custom_dirs_and_extensions(case_dir):
    workdir = copy_fixture_tree("autogen_custom", case_dir)

    _result, data = run_itool_json(
        [
            "ag",
            "idf",
            "sol.py",
            "-g",
            "cat",
            "--input",
            "indata",
            "--output",
            "outdata",
            "--inext",
            "dat",
            "--outext",
            "ans",
            "-j",
            "1",
        ],
        cwd=workdir,
    )

    assert (workdir / "indata" / "1.a.dat").read_text() == "5\n"
    assert (workdir / "indata" / "1.b.dat").read_text() == "6\n"
    assert (workdir / "outdata" / "1.a.ans").read_text() == "5\n"
    assert (workdir / "outdata" / "1.b.ans").read_text() == "6\n"
    assert len(data) == 1
    assert data[0]["name"] == "sol.py"
    assert data[0]["result"] == "OK"


def test_autogenerate_idf_version_switch(case_dir):
    workdir = copy_fixture_tree("autogen_v1", case_dir)

    run_itool_json(
        ["ag", "idf", "sol.py", "-g", "cat", "--idf-version", "1", "-j", "1"],
        cwd=workdir,
    )

    assert (workdir / "test" / "legacy.a.in").exists()
    assert (workdir / "test" / "legacy.a.out").exists()
    assert (workdir / "test" / "legacy.a.in").read_text() == "1\n"
    assert (workdir / "test" / "legacy.a.out").read_text() == "1\n"


def test_autogenerate_pythoncmd_override(case_dir):
    workdir = copy_fixture_tree("autogen_pygen", case_dir)

    result, data = run_itool_json(
        [
            "ag",
            "idf",
            "sol.py",
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
    assert len(data) == 1
    assert data[0]["name"] == "sol.py"
    assert data[0]["result"] == "OK"


def test_autogenerate_no_compile_requires_prebuilt_programs(case_dir):
    workdir = copy_fixture_tree("autogen_cpp", case_dir)

    _result, data = run_itool_json(
        ["ag", "idf", "sol.cpp", "-g", "cat", "--no-compile", "-j", "1"], cwd=workdir
    )

    assert len(data) == 1
    assert data[0]["name"] == "sol.cpp"
    assert data[0]["result"] in {"EXC", "WA", "TLE"}


def test_autogenerate_execute_mode(case_dir):
    workdir = copy_fixture_tree("autogen_custom", case_dir)

    _result, data = run_itool_json(
        ["ag", "idf", "cat", "-g", "cat", "--execute", "-j", "1"], cwd=workdir
    )

    assert (workdir / "test" / "1.a.in").exists()
    assert (workdir / "test" / "1.a.out").read_text() == "5\n"
    assert (workdir / "test" / "1.b.out").read_text() == "6\n"
    assert len(data) == 1
    assert data[0]["name"] == "cat"
    assert data[0]["result"] == "OK"


def test_autogenerate_execute_nonexistent_solution_is_not_ok(case_dir):
    workdir = copy_fixture_tree("autogen_custom", case_dir)

    _result, data = run_itool_json(
        ["ag", "idf", "definitely_missing_cmd", "-g", "cat", "--execute", "-j", "1"],
        cwd=workdir,
    )

    assert len(data) == 1
    assert data[0]["name"] == "definitely_missing_cmd"
    assert data[0]["result"] in {"EXC", "WA", "TLE"}


def test_autogenerate_progdir_override(case_dir):
    workdir = copy_fixture_tree("autogen_cpp", case_dir)

    _result, data = run_itool_json(
        ["ag", "idf", "sol.cpp", "-g", "cat", "--progdir", "build", "-j", "1"],
        cwd=workdir,
    )

    assert (workdir / "build" / "sol").exists()
    assert len(data) == 1
    assert data[0]["name"] == "sol.cpp"
    assert data[0]["result"] == "OK"


def test_autogenerate_no_statistics_hides_summary(case_dir):
    workdir = copy_fixture_tree("autogen_custom", case_dir)

    result = run_itool(
        ["ag", "idf", "sol.py", "-g", "cat", "--no-statistics", "-j", "1"],
        cwd=workdir,
    )

    assert "| Solution" not in result.stdout
