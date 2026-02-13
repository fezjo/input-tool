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
