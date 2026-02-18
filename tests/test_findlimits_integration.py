import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest
from test_utils import copy_fixture_tree, filter_out_ansi_escape_codes, run_itool

from input_tool.input_findlimits import (
    SolutionExpectation,
    SolutionTimingData,
    TimelimitConstraint,
    _find_best_compromise,
    _robust_max,
    compute_retry_cap,
    compute_timelimit_for_language,
    find_solutions_needing_retry,
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
    assert 0.03 < tl < 1.0, (
        f"Recommended timelimit {tl:.3f}s is outside expected range (0.03, 1.0)"
    )


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
    assert 0.3 < high < 1.5, (
        f"valid_max {high:.3f}s is outside expected range (0.3, 1.5)"
    )

    # The range should be non-degenerate: low < high
    assert low < high, f"Invalid range: [{low:.3f}, {high:.3f}]"


@pytest.mark.timing_sensitive
def test_findlimits_basic_all_constraints_satisfied(case_dir):
    """All constraints should be satisfiable with the recommended timelimit."""
    workdir = copy_fixture_tree("findlimits_basic", case_dir)
    output = _run_findlimits(workdir)

    # Should say "All N constraints satisfied"
    assert re.search(r"All \d+ constraints satisfied", output), (
        f"Not all constraints satisfied:\n{output}"
    )


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
    assert re.search(r"Recommended -t flag:\s+py=[\d.]+", output), (
        f"No recommended -t flag found:\n{output}"
    )


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
    assert recommended1 == recommended2, (
        f"Cached results differ: {recommended1} != {recommended2}"
    )


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


# ==================== Retry Integration Tests ====================


def _run_findlimits_retry(workdir: Path, extra_args: Optional[list] = None) -> str:
    """Run findlimits on retry fixture with a low baseline multiplier."""
    args = ["fl", ".", "-q", "--max-timelimit", "5", "--baseline-multiplier", "3"]
    if extra_args:
        args.extend(extra_args)
    result = run_itool(args, cwd=workdir, threads=None)
    return filter_out_ansi_escape_codes(result.stdout)


@pytest.mark.timing_sensitive
def test_retry_discovers_actual_time(case_dir):
    """After retry, outlier solution should have actual times (not TLE) in final table."""
    workdir = copy_fixture_tree("findlimits_retry", case_dir)
    output = _run_findlimits_retry(workdir)

    # Should see at least one retry pass
    assert "Retry Pass" in output, f"No retry pass found in output:\n{output}"

    # After retry, timing table should show sol-4-outlier.py with all OOOO
    # (not OOOT). Find the "Actual" column for this solution.
    found_outlier_actual = False
    for line in output.splitlines():
        if "sol-4-outlier.py" in line and "OOOO" in line:
            found_outlier_actual = True
            break
    assert found_outlier_actual, (
        f"sol-4-outlier.py should show OOOO after retry:\n{output}"
    )


@pytest.mark.timing_sensitive
def test_retry_all_constraints_satisfied(case_dir):
    """After retry, all constraints should be satisfied."""
    workdir = copy_fixture_tree("findlimits_retry", case_dir)
    output = _run_findlimits_retry(workdir)

    assert re.search(r"All \d+ constraints satisfied", output), (
        f"Not all constraints satisfied after retry:\n{output}"
    )


@pytest.mark.timing_sensitive
def test_retry_outlier_time_in_valid_range(case_dir):
    """Outlier's batch 4 time (~0.6s) should appear in the valid range."""
    workdir = copy_fixture_tree("findlimits_retry", case_dir)
    output = _run_findlimits_retry(workdir)

    ranges = _parse_valid_range(output)
    assert "python" in ranges, f"No python range found in output:\n{output}"

    low, _high = ranges["python"]
    # valid_min should include the outlier's batch 4 time (~0.6s + overhead)
    assert low > 0.4, f"valid_min {low:.3f}s is too low, should include outlier time"


@pytest.mark.timing_sensitive
def test_retry_partial_solution_not_retried(case_dir):
    """sol-2-partial.py should NOT be retried (its TLEs are expected)."""
    workdir = copy_fixture_tree("findlimits_retry", case_dir)
    output = _run_findlimits_retry(workdir)

    # Retry sections mention "Retrying <name>". Check that only
    # the outlier is retried, not the partial solution.
    retrying_lines = [line for line in output.splitlines() if "Retrying " in line]
    for line in retrying_lines:
        assert "sol-2-partial.py" not in line, (
            f"sol-2-partial.py should not be retried:\n{output}"
        )


@pytest.mark.timing_sensitive
def test_retry_iterates_until_success(case_dir):
    """With baseline_multiplier=3, retry should take multiple rounds for the outlier."""
    workdir = copy_fixture_tree("findlimits_retry", case_dir)
    output = _run_findlimits_retry(workdir)

    # Count retry passes — should be at least 2 with multiplier=3 and
    # outlier sleeping 0.6s (initial cap ~0.13s, round 1 ~0.39s, round 2 ~1.17s)
    retry_passes = re.findall(r"Retry Pass \d+", output)
    assert len(retry_passes) >= 2, (
        f"Expected at least 2 retry passes, got {len(retry_passes)}:\n{output}"
    )


# ==================== Unit Tests for Retry/Outlier Functions ====================


class TestRobustMax:
    def test_empty(self):
        assert _robust_max([]) == 0.0

    def test_single_value(self):
        assert _robust_max([5.0]) == 5.0

    def test_three_values_uses_max(self):
        """With < 4 values, falls back to true max."""
        assert _robust_max([1.0, 2.0, 3.0]) == 3.0

    def test_four_values_uses_p75(self):
        """With 4+ values, uses P75 instead of max."""
        result = _robust_max([1.0, 2.0, 3.0, 100.0])
        # P75 of [1, 2, 3, 100] is at index 2.25 -> lerp(3, 100, 0.25) = 27.25
        assert result < 100.0, "Should be less than the outlier max"
        assert result > 2.0, "Should be above the median"

    def test_outlier_protection(self):
        """One outlier should not dominate the result."""
        normal = [0.05, 0.06, 0.07, 0.08]
        with_outlier = [0.05, 0.06, 0.07, 0.08, 1.5]
        normal_max = _robust_max(normal)
        outlier_result = _robust_max(with_outlier)
        # With outlier, P75 should be much less than 1.5
        assert outlier_result < 0.5, (
            f"Outlier should not dominate: got {outlier_result}"
        )
        # But should still be >= normal max (since P75 of 5 values
        # is at index 3 which is 0.08)
        assert outlier_result >= normal_max - 0.01

    def test_custom_percentile(self):
        result = _robust_max([1.0, 2.0, 3.0, 4.0, 5.0], percentile=50.0)
        # P50 of [1,2,3,4,5] at index 2.0 -> 3.0
        assert abs(result - 3.0) < 0.01


class TestFindSolutionsNeedingRetry:
    """Test the retry detection logic."""

    def _make_expectation(
        self,
        name: str,
        batch_string: Optional[str] = None,
        expected_ok: Optional[int] = None,
    ) -> SolutionExpectation:
        """Create a mock SolutionExpectation."""
        from unittest.mock import MagicMock

        from input_tool.common.commands import Langs

        sol = MagicMock()
        sol.name = name
        exp = SolutionExpectation(
            solution=sol,
            lang=Langs.Lang.python,
            batch_string=batch_string,
            positional=batch_string is not None,
            expected_ok_count=expected_ok,
        )
        return exp

    def _make_timing(
        self,
        name: str,
        batch_statuses: Dict[str, str],
        batch_times: Dict[str, Optional[float]],
        cap: float = 1.0,
    ) -> SolutionTimingData:
        return SolutionTimingData(
            name=name,
            lang="python",
            batch_max_times=batch_times,
            batch_statuses=batch_statuses,
            timelimit_used=cap,
        )

    def test_positional_tle_on_expected_pass(self):
        """Positional: batch expected O but got T -> needs retry."""
        exp = self._make_expectation("sol", batch_string="OOOT")
        td = self._make_timing(
            "sol",
            {"1": "O", "2": "O", "3": "O", "4": "T"},
            {"1": 0.1, "2": 0.1, "3": 0.1, "4": None},
        )
        result = find_solutions_needing_retry({"sol": td}, [exp], ["1", "2", "3", "4"])
        assert len(result) == 0  # batch 4 expected T, so no retry

    def test_positional_tle_on_expected_ok(self):
        """Positional: batch expected O but got T -> needs retry."""
        exp = self._make_expectation("sol", batch_string="OOOO")
        td = self._make_timing(
            "sol",
            {"1": "O", "2": "O", "3": "O", "4": "T"},
            {"1": 0.1, "2": 0.1, "3": 0.1, "4": None},
        )
        result = find_solutions_needing_retry({"sol": td}, [exp], ["1", "2", "3", "4"])
        assert len(result) == 1
        assert result[0][1] == ["4"]

    def test_positional_tle_on_expected_wa(self):
        """Positional: batch expected W but got T -> needs retry."""
        exp = self._make_expectation("sol", batch_string="OOWT")
        td = self._make_timing(
            "sol",
            {"1": "O", "2": "O", "3": "T", "4": "T"},
            {"1": 0.1, "2": 0.1, "3": None, "4": None},
        )
        result = find_solutions_needing_retry({"sol": td}, [exp], ["1", "2", "3", "4"])
        assert len(result) == 1
        assert result[0][1] == ["3"]  # batch 3 expected W, got T

    def test_nonpositional_enough_ok(self):
        """Non-positional: 2 expected, 2 OK observed -> no retry."""
        exp = self._make_expectation("sol", expected_ok=2)
        td = self._make_timing(
            "sol",
            {"1": "O", "2": "O", "3": "T", "4": "T"},
            {"1": 0.1, "2": 0.1, "3": None, "4": None},
        )
        result = find_solutions_needing_retry({"sol": td}, [exp], ["1", "2", "3", "4"])
        assert len(result) == 0

    def test_nonpositional_not_enough_ok(self):
        """Non-positional: 3 expected, only 1 OK -> needs retry."""
        exp = self._make_expectation("sol", expected_ok=3)
        td = self._make_timing(
            "sol",
            {"1": "O", "2": "T", "3": "T", "4": "T"},
            {"1": 0.1, "2": None, "3": None, "4": None},
        )
        result = find_solutions_needing_retry({"sol": td}, [exp], ["1", "2", "3", "4"])
        assert len(result) == 1
        assert sorted(result[0][1]) == ["2", "3", "4"]

    def test_nonpositional_wa_counts_as_ok(self):
        """Non-positional: WA batches count toward non-TLE count."""
        exp = self._make_expectation("sol", expected_ok=2)
        td = self._make_timing(
            "sol",
            {"1": "O", "2": "W", "3": "T", "4": "T"},
            {"1": 0.1, "2": 0.1, "3": None, "4": None},
        )
        result = find_solutions_needing_retry({"sol": td}, [exp], ["1", "2", "3", "4"])
        # O + W = 2 >= expected 2 -> no retry
        assert len(result) == 0


class TestComputeRetryCap:
    def test_increases_from_previous(self):
        td = SolutionTimingData(
            name="sol",
            lang="python",
            batch_max_times={"1": None},
            batch_statuses={"1": "T"},
            timelimit_used=0.5,
        )
        cap = compute_retry_cap(td, {"1": 0.05}, 3.0, 10.0)
        assert cap == 1.5  # 3 * 0.5 = 1.5 > 3 * 0.05 = 0.15

    def test_bounded_by_max_timelimit(self):
        td = SolutionTimingData(
            name="sol",
            lang="python",
            batch_max_times={"1": None},
            batch_statuses={"1": "T"},
            timelimit_used=5.0,
        )
        cap = compute_retry_cap(td, {"1": 0.05}, 3.0, 10.0)
        assert cap == 10.0  # 3 * 5.0 = 15.0, capped at 10.0

    def test_uses_baseline_when_higher(self):
        td = SolutionTimingData(
            name="sol",
            lang="python",
            batch_max_times={"1": None},
            batch_statuses={"1": "T"},
            timelimit_used=0.1,
        )
        cap = compute_retry_cap(td, {"1": 0.5}, 10.0, 20.0)
        # 3 * 0.1 = 0.3, but baseline 10 * 0.5 = 5.0 is higher
        assert cap == 5.0


class TestLowerBoundConstraints:
    """Test that lower_bound constraints are handled correctly."""

    def test_lower_bound_never_satisfied_in_compromise(self):
        """lower_bound constraints should never count as satisfied."""
        constraints = [
            TimelimitConstraint("sol1", "1", "must_pass", 0.1),
            TimelimitConstraint("sol2", "2", "must_pass", 0.5, lower_bound=True),
            TimelimitConstraint("sol3", "3", "must_tle", 1.0),
        ]
        tl, satisfied, unsatisfied = _find_best_compromise(
            constraints, 0.1, 1.0, hint=0.5
        )
        # Only 2 non-lower_bound constraints can be satisfied
        assert satisfied <= 2
        # The lower_bound constraint should be in unsatisfied
        lower_bound_msgs = [m for m in unsatisfied if "needs rerun" in m]
        assert len(lower_bound_msgs) == 1

    def test_lower_bound_excluded_from_valid_min(self):
        """lower_bound constraints should not affect valid_min computation."""
        from input_tool.common.commands import Langs

        # Create timing data where a solution TLE'd at 0.5s cap
        timing_data = {
            "sol-fast": SolutionTimingData(
                name="sol-fast",
                lang="python",
                batch_max_times={"1": 0.05, "2": 0.1},
                batch_statuses={"1": "O", "2": "O"},
                timelimit_used=1.0,
            ),
            "sol-slow": SolutionTimingData(
                name="sol-slow",
                lang="python",
                batch_max_times={"1": 0.05, "2": None},
                batch_statuses={"1": "O", "2": "T"},
                timelimit_used=0.5,
            ),
        }

        from unittest.mock import MagicMock

        fast_sol = MagicMock()
        fast_sol.name = "sol-fast"
        slow_sol = MagicMock()
        slow_sol.name = "sol-slow"

        expectations = [
            SolutionExpectation(
                solution=fast_sol,
                lang=Langs.Lang.python,
                batch_string="OO",
                positional=True,
            ),
            SolutionExpectation(
                solution=slow_sol,
                lang=Langs.Lang.python,
                batch_string="OO",
                positional=True,
            ),
        ]

        result = compute_timelimit_for_language(
            Langs.Lang.python, timing_data, expectations, ["1", "2"]
        )

        # valid_min should be based on real constraints only (0.1s from sol-fast)
        # not the lower_bound from sol-slow's TLE at 0.5s
        assert result.valid_min is not None
        assert result.valid_min < 0.5, (
            f"valid_min {result.valid_min} should not include lower_bound time 0.5"
        )

        # There should be unsatisfied lower_bound constraints
        assert not result.all_satisfied
        lower_bound_msgs = [m for m in result.unsatisfied if "needs rerun" in m]
        assert len(lower_bound_msgs) >= 1
