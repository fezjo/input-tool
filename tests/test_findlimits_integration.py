import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest
from test_utils import copy_fixture_tree, filter_out_ansi_escape_codes, run_itool

from input_tool.input_findlimits import (
    infer_ok_count,
    parse_batch_string,
    parse_score,
    parse_verdict_tag,
)


def _run_findlimits(workdir: Path, extra_args: Optional[list] = None) -> str:
    """Run findlimits on a workdir and return the cleaned stdout."""
    args = ["fl", ".", "-q", "--max-timelimit", "5", "--baseline-multiplier", "15"]
    if extra_args:
        args.extend(extra_args)
    result = run_itool(args, cwd=workdir, threads=None)
    return filter_out_ansi_escape_codes(result.stdout)


def _parse_recommended(output: str) -> Dict[str, float]:
    """Extract recommended timelimits per language from findlimits output.

    Looks for lines like: "Recommended timelimit: 0.16s"
    preceded by a "Language: python" line.
    """
    results: Dict[str, float] = {}
    current_lang = None
    for line in output.splitlines():
        lang_match = re.search(r"Language:\s+(\w+)", line)
        if lang_match:
            current_lang = lang_match.group(1)
        tl_match = re.search(r"Recommended timelimit:\s+([\d.]+)s", line)
        if tl_match and current_lang:
            results[current_lang] = float(tl_match.group(1))
    return results


def _parse_valid_range(output: str) -> Dict[str, Tuple[float, float]]:
    """Extract valid timelimit ranges per language from findlimits output.

    Looks for lines like: "Valid range: [0.050s, 0.500s]"
    or "Valid range: [0.050s, +inf)"
    """
    results: Dict[str, Tuple[float, float]] = {}
    current_lang = None
    for line in output.splitlines():
        lang_match = re.search(r"Language:\s+(\w+)", line)
        if lang_match:
            current_lang = lang_match.group(1)
        range_match = re.search(
            r"Valid range:\s*\[([\d.]+)s,\s*(?:([\d.]+)s|\+inf)[)\]]", line
        )
        if range_match and current_lang:
            low = float(range_match.group(1))
            high = float(range_match.group(2)) if range_match.group(2) else float("inf")
            results[current_lang] = (low, high)
    return results


@pytest.mark.timing_sensitive
def test_findlimits_basic_recommended_timelimit(case_dir):
    """findlimits should recommend a timelimit in the valid range for the basic fixture.

    Fixture has 3 batches with increasing input sizes (10, 20, 500).
    - sol-3-fast.py: score 3, all pass fast (sleep n/10000)
    - sol-2-slow.py: score 2, batch 3 is slow (sleep n/1000 -> 0.5s)
    - sol-0-WA-wrong.py: WA tagged, all fast, outputs wrong answer

    Expected valid range: roughly (max_pass_time, 0.5s).
    The recommended timelimit should be the geometric mean of the range bounds.
    """
    workdir = copy_fixture_tree("findlimits_basic", case_dir)
    output = _run_findlimits(workdir)

    recommended = _parse_recommended(output)
    assert "python" in recommended, f"No python timelimit found in output:\n{output}"

    tl = recommended["python"]
    # The recommended TL should be strictly between the fastest must_pass
    # (~0.05s + Python overhead) and the slowest must_tle (~0.5s + overhead).
    # With Python startup overhead, actual times are higher, so use generous bounds.
    assert (
        0.03 < tl < 1.0
    ), f"Recommended timelimit {tl:.3f}s is outside expected range (0.03, 1.0)"


@pytest.mark.timing_sensitive
def test_findlimits_basic_valid_range(case_dir):
    """The valid range should span from the slowest must_pass time
    to the fastest must_tle time."""
    workdir = copy_fixture_tree("findlimits_basic", case_dir)
    output = _run_findlimits(workdir)

    ranges = _parse_valid_range(output)
    assert "python" in ranges, f"No python range found in output:\n{output}"

    low, high = ranges["python"]
    # valid_min should be at least 0.02s (sol-2-slow batch 2 time)
    # but could be higher with Python overhead
    assert low >= 0.01, f"valid_min {low:.3f}s is too low"
    assert low < 0.5, f"valid_min {low:.3f}s is too high (should be well below 0.5s)"

    # valid_max should be around 0.5s (sol-2-slow batch 3 time) + Python overhead
    # With baseline_multiplier=15, sol-2-slow should actually finish batch 3
    # so we should get a concrete upper bound.
    assert (
        0.3 < high < 1.5
    ), f"valid_max {high:.3f}s is outside expected range (0.3, 1.5)"

    # The range should be non-degenerate: low < high
    assert low < high, f"Invalid range: [{low:.3f}, {high:.3f}]"


@pytest.mark.timing_sensitive
def test_findlimits_basic_all_constraints_satisfied(case_dir):
    """All constraints should be satisfiable with the recommended timelimit."""
    workdir = copy_fixture_tree("findlimits_basic", case_dir)
    output = _run_findlimits(workdir)

    # Should say "All N constraints satisfied"
    assert re.search(
        r"All \d+ constraints satisfied", output
    ), f"Not all constraints satisfied:\n{output}"


@pytest.mark.timing_sensitive
def test_findlimits_basic_wa_solution_display(case_dir):
    """sol-0-WA-wrong.py should be shown with [WA] tag in expectations."""
    workdir = copy_fixture_tree("findlimits_basic", case_dir)
    output = _run_findlimits(workdir)

    # The expectations table should show WA tag
    assert "[WA]" in output, f"WA tag not shown in output:\n{output}"


@pytest.mark.timing_sensitive
def test_findlimits_basic_recommended_flag(case_dir):
    """The output should include a recommended -t flag string."""
    workdir = copy_fixture_tree("findlimits_basic", case_dir)
    output = _run_findlimits(workdir)

    # Should have a recommended -t flag line like "Recommended -t flag: py=0.2"
    assert re.search(
        r"Recommended -t flag:\s+py=[\d.]+", output
    ), f"No recommended -t flag found:\n{output}"


@pytest.mark.timing_sensitive
def test_findlimits_basic_cache_reuse(case_dir):
    """Running findlimits twice should reuse cached results on the second run."""
    workdir = copy_fixture_tree("findlimits_basic", case_dir)

    # First run
    output1 = _run_findlimits(workdir)
    recommended1 = _parse_recommended(output1)
    assert "python" in recommended1

    # Cache file should exist
    cache_file = workdir / "test" / ".findlimits_cache.json"
    assert cache_file.exists(), "Cache file not created after first run"

    # Second run should use cache
    output2 = _run_findlimits(workdir)
    assert "cached" in output2.lower(), f"Second run doesn't mention cache:\n{output2}"

    # Results should be identical
    recommended2 = _parse_recommended(output2)
    assert (
        recommended1 == recommended2
    ), f"Cached results differ: {recommended1} != {recommended2}"


@pytest.mark.timing_sensitive
def test_findlimits_basic_expectations_table(case_dir):
    """The output should show parsed expectations for all solutions."""
    workdir = copy_fixture_tree("findlimits_basic", case_dir)
    output = _run_findlimits(workdir)

    # Should list all three solutions
    assert "sol-3-fast.py" in output
    assert "sol-2-slow.py" in output
    assert "sol-0-WA-wrong.py" in output

    # Should show batch count expectations
    assert "(3/3 OK)" in output or "(3 OK)" in output
    assert "(2/3 OK)" in output or "(2 OK)" in output
    assert "(0/3 OK)" in output or "(0 OK)" in output


# ==================== Unit Tests for Parsing Functions ====================


class TestParseBatchString:
    def test_simple_batch_string(self):
        assert parse_batch_string("sol-75-OOOT.py") == "OOOT"

    def test_all_ok(self):
        assert parse_batch_string("sol-100-OOO.cpp") == "OOO"

    def test_mixed_statuses(self):
        assert parse_batch_string("sol-OOWTEE.py") == "OOWTEE"

    def test_no_batch_string(self):
        assert parse_batch_string("sol-100-fast.py") is None

    def test_single_char_not_matched(self):
        """Single character segments like 'O' should not match (minimum 2)."""
        assert parse_batch_string("sol-O-fast.py") is None

    def test_batch_string_with_score(self):
        assert parse_batch_string("sol-60-OOOWT-dp-n2.py") == "OOOWT"

    def test_invalid_chars(self):
        """Segments with non-OWTE characters should not match."""
        assert parse_batch_string("sol-OOXO.py") is None

    def test_lowercase_not_matched(self):
        assert parse_batch_string("sol-ooot.py") is None

    def test_wa_tag_not_batch_string(self):
        """WA contains 'A' which is not in OWTE, so it should not match."""
        assert parse_batch_string("sol-WA.py") is None

    def test_two_char_valid(self):
        """Minimum 2 valid chars like 'OT' should match."""
        assert parse_batch_string("sol-OT.py") == "OT"


class TestParseScore:
    def test_simple_score(self):
        assert parse_score("sol-100.py") == 100

    def test_zero_score(self):
        assert parse_score("sol-0.py") == 0

    def test_score_with_suffix(self):
        assert parse_score("sol-3-TLE-slow.cpp") == 3

    def test_no_score(self):
        assert parse_score("sol-fast.py") is None

    def test_no_parts(self):
        assert parse_score("solution.py") is None

    def test_negative_not_numeric(self):
        """Negative numbers use isnumeric which rejects '-'."""
        assert parse_score("sol--1.py") is None


class TestParseVerdictTag:
    def test_tle_tag(self):
        assert parse_verdict_tag("sol-3-TLE-slow.py") == "TLE"

    def test_wa_tag(self):
        assert parse_verdict_tag("sol-0-WA-wrong.py") == "WA"

    def test_exc_tag(self):
        assert parse_verdict_tag("sol-0-EXC-crash.py") == "EXC"

    def test_no_tag(self):
        assert parse_verdict_tag("sol-100-fast.py") is None

    def test_case_insensitive(self):
        assert parse_verdict_tag("sol-3-tle.py") == "TLE"

    def test_wa_in_middle(self):
        assert parse_verdict_tag("sol-0-WA-base1.py") == "WA"


class TestInferOkCount:
    def test_raw_count(self):
        assert infer_ok_count(3, 5) == 3

    def test_percentage(self):
        assert infer_ok_count(75, 4) == 3

    def test_percentage_rounding(self):
        assert infer_ok_count(67, 3) == 2

    def test_zero(self):
        assert infer_ok_count(0, 5) == 0

    def test_full_score_raw(self):
        assert infer_ok_count(5, 5) == 5

    def test_full_score_percentage(self):
        assert infer_ok_count(100, 5) == 5

    def test_boundary_score_equals_batches(self):
        """When score == num_batches, treat as raw count."""
        assert infer_ok_count(8, 8) == 8
