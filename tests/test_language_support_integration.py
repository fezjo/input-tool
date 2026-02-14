import shutil
import warnings

import pytest

from test_utils import copy_fixture_tree, run_itool, run_itool_json


def _language_programs_and_missing() -> tuple[list[str], list[str]]:
    has_make = shutil.which("make") is not None
    programs: list[str] = []
    missing: list[str] = []

    if has_make and (shutil.which("cc") or shutil.which("gcc")):
        programs.append("sol_c.c")
    else:
        missing.append("C (requires make + cc/gcc)")

    if has_make and (shutil.which("c++") or shutil.which("g++")):
        programs.append("sol_cpp.cpp")
    else:
        missing.append("C++ (requires make + c++/g++)")

    if shutil.which("fpc"):
        programs.append("sol_pas.pas")
    else:
        missing.append("Pascal (requires fpc)")

    if shutil.which("javac") and shutil.which("java"):
        programs.append("sol_java.java")
    else:
        missing.append("Java (requires javac + java)")

    if shutil.which("rustc"):
        programs.append("sol_rs.rs")
    else:
        missing.append("Rust (requires rustc)")

    if shutil.which("ghc"):
        programs.append("sol_hs.hs")
    else:
        missing.append("Haskell (requires ghc)")

    if shutil.which("python3") or shutil.which("python") or shutil.which("pypy3"):
        programs.append("sol_py.py")
    else:
        missing.append("Python (requires python3/python/pypy3)")

    if shutil.which("node") or shutil.which("nodejs"):
        programs.append("sol_js.js")
    else:
        missing.append("JavaScript (requires node/nodejs)")

    if shutil.which("sh") and shutil.which("cat"):
        programs.append("sol_py_exe.py")
    else:
        missing.append("Executable Python (requires sh + cat)")

    return programs, missing


def _warn_missing_toolchains(missing: list[str]) -> None:
    if missing:
        warnings.warn(
            "Some language toolchains are unavailable; skipping those language"
            f" checks: {', '.join(missing)}",
            stacklevel=2,
        )


def test_supported_languages_can_be_compiled(case_dir):
    workdir = copy_fixture_tree("lang_matrix", case_dir)
    programs, missing = _language_programs_and_missing()

    _warn_missing_toolchains(missing)

    if not programs:
        pytest.xfail(
            "No supported language toolchains are available in this environment."
        )

    result = run_itool(
        ["c", *programs, "--progdir", "build", "-j", "1"],
        cwd=workdir,
    )

    assert result.returncode == 0


def test_supported_languages_can_be_tested(case_dir):
    workdir = copy_fixture_tree("lang_matrix", case_dir)
    programs, missing = _language_programs_and_missing()

    _warn_missing_toolchains(missing)

    if not programs:
        pytest.xfail(
            "No supported language toolchains are available in this environment."
        )

    _result, data = run_itool_json(
        ["t", *programs, "--progdir", "build", "--no-statistics", "-t", "0", "-j", "1"],
        cwd=workdir,
    )

    assert len(data) == len(programs)
    assert {row["name"] for row in data} == set(programs)
    print(data)
    assert all(row["result"] == "OK" for row in data)


def test_supported_languages_in_dir_can_be_compiled(case_dir):
    workdir = copy_fixture_tree("lang_matrix_dir", case_dir)
    programs, missing = _language_programs_and_missing()

    _warn_missing_toolchains(missing)

    if not programs:
        pytest.xfail(
            "No supported language toolchains are available in this environment."
        )
    programs = [f"src/{p}" for p in programs]

    result = run_itool(
        ["c", *programs, "--progdir", "build", "-j", "1"],
        cwd=workdir,
    )

    assert result.returncode == 0


def test_supported_languages_in_dir_can_be_tested(case_dir):
    workdir = copy_fixture_tree("lang_matrix_dir", case_dir)
    programs, missing = _language_programs_and_missing()

    _warn_missing_toolchains(missing)

    if not programs:
        pytest.xfail(
            "No supported language toolchains are available in this environment."
        )
    programs = [f"src/{p}" for p in programs]

    _result, data = run_itool_json(
        ["t", *programs, "--progdir", "build", "--no-statistics", "-t", "0", "-j", "1"],
        cwd=workdir,
    )

    assert len(data) == len(programs)
    assert {row["name"] for row in data} == set(programs)
    print(data)
    assert all(row["result"] == "OK" for row in data)
