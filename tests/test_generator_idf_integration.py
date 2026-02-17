from test_utils import copy_fixture_tree, get_input_files, run_itool


def test_idf_v2_yaml_eval_merge_nofile_multiline_and_escape(case_dir):
    workdir = copy_fixture_tree("idf_v2_commands", case_dir)

    run_itool(["g", ".", "-g", "cat", "--idf-version", "2"], cwd=workdir)

    assert (workdir / "test" / "x.a.in").read_text() == "1 3 6\n"
    assert (workdir / "test" / "x.b.in").read_text() == "2 b\n"
    assert not (workdir / "test" / "x.c.in").exists()
    assert (workdir / "test" / "x.d.in").read_text() == "line1\n~line2\n"
    assert (workdir / "test" / "1.e.in").read_text() == "{{name}} {name}\n"
    assert get_input_files(workdir / "test") == ["1.e.in", "x.a.in", "x.b.in", "x.d.in"]


def test_idf_v1_legacy_equals_commands_work(case_dir):
    workdir = copy_fixture_tree("idf_v1_legacy", case_dir)

    run_itool(["g", ".", "-g", "cat", "--idf-version", "1"], cwd=workdir)

    assert (workdir / "test" / "legacy.a.in").read_text() == "1 hello\n"
    assert (workdir / "test" / "1.b.in").read_text() == "2 world\n"
    assert get_input_files(workdir / "test") == ["1.b.in", "legacy.a.in"]


def test_idf_v2_rejects_nonboolean_nofile(case_dir):
    workdir = copy_fixture_tree("idf_v2_invalid_nofile", case_dir)

    result = run_itool(
        ["g", ".", "-g", "cat", "--idf-version", "2"], cwd=workdir, check=False
    )

    assert result.returncode != 0
    assert "nofile must be boolean" in result.stdout
    assert "Errors in recipe, exiting" in result.stdout


def test_generate_directory_fails_when_multiple_idf_files_exist(case_dir):
    workdir = copy_fixture_tree("idf_multiple", case_dir)

    result = run_itool(["g", ".", "-g", "cat"], cwd=workdir, check=False)

    assert result.returncode != 0
    assert "Found 2 idf files" in result.stdout
