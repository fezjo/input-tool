import pytest

from test_utils import run_itool


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["--version"],
        ["t", "--help"],
        ["test", "--help-all"],
        ["g", "--help"],
        ["generate", "--help-all"],
        ["s", "--help"],
        ["sample", "--help-all"],
        ["c", "--help"],
        ["compile", "--help-all"],
        ["ag", "--help"],
        ["autogenerate", "--help-all"],
        ["colortest", "--help"],
        ["checkupdates", "--help"],
    ],
)
def test_cli_flags_exit_zero(case_dir, args):
    result = run_itool(args, cwd=case_dir, check=False)
    assert result.returncode == 0


@pytest.mark.parametrize(
    "args",
    [
        ["unknown-subcommand"],
        ["t", "--unknown-flag"],
        ["g", "--unknown-flag"],
        ["sample", "--unknown-flag"],
        ["compile", "--unknown-flag"],
        ["autogenerate", "--unknown-flag"],
        ["colortest", "--unknown-flag"],
    ],
)
def test_cli_flags_exit_nonzero(case_dir, args):
    result = run_itool(args, cwd=case_dir, check=False)
    assert result.returncode != 0
