#!/usr/bin/env python3
# © 2026 fezjo
# Find optimal per-language timelimits from solution expectations.
# DISCLAIMER: This file is purely vibe coded, don't judge it and don't judge me.
import json
import math
import os
import re
import threading
import time
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Sequence

from input_tool.common.commands import Config, Langs, natural_sort_key
from input_tool.common.messages import (
    BufferedLogger,
    ParallelLoggerManager,
    Status,
    default_logger,
    fatal,
    info,
    infob,
    plain,
    stylized_tqdm,
    warning,
)
from input_tool.common.parser.specifications import ArgsFindlimits
from input_tool.common.programs.checker import Checker
from input_tool.common.programs.solution import Solution
from input_tool.common.programs.validator import Validator
from input_tool.common.task_history import TASK_HISTORY
from input_tool.common.task_queue import TaskItem, TaskQueue
from input_tool.common.tools_common import (
    check_data_folder_size,
    cleanup,
    prepare_programs,
    register_quit_with_executor,
    setup_config,
)
from input_tool.common.types import Directory, Path, RelativePath, TempFile
from input_tool.input_tester import (
    create_programs_from_files,
    deduplicate_solutions,
    get_relevant_prog_files_deeper,
    sorted_files_with_ext,
)

# ==================== Expectation Parsing ====================

BATCH_RESULT_RE = re.compile(r"^[OWTE]{2,}$")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    """Remove ANSI escape codes from string for width calculation."""
    return ANSI_RE.sub("", s)


@dataclass
class SolutionExpectation:
    solution: Solution
    lang: Langs.Lang
    # Positional batch expectations: e.g. "OOOWT" -> {0:'O', 1:'O', 2:'O', 3:'W', 4:'T'}
    # None if not available (inferred from score)
    batch_string: Optional[str] = None
    # Number of OK batches expected (inferred from score when no batch string)
    expected_ok_count: Optional[int] = None
    # Whether this has a positional (batch string) expectation
    positional: bool = False
    # Whether filename contains a TLE/WA verdict tag (for warnings)
    verdict_tag: Optional[str] = None
    # Score parsed from filename
    score: Optional[int] = None


def parse_batch_string(name: str) -> Optional[str]:
    """Extract batch result string from solution filename.

    Scans dash-separated parts for the first all-uppercase segment
    consisting only of O, W, T, E characters (at least 2 chars).
    """
    stem = Path(name).stem
    parts = stem.split("-")
    for part in parts:
        if BATCH_RESULT_RE.match(part):
            return part
    return None


def parse_score(name: str) -> Optional[int]:
    """Extract numeric score from solution filename (parts[1] if numeric)."""
    stem = Path(name).stem
    parts = stem.split("-")
    if len(parts) > 1 and parts[1].isnumeric():
        return int(parts[1])
    return None


def parse_verdict_tag(name: str) -> Optional[str]:
    """Check if filename contains TLE or WA as a dash-separated part."""
    stem = Path(name).stem
    parts = stem.split("-")
    for part in parts:
        up = part.upper()
        if up in ("TLE", "WA", "EXC"):
            return up
    return None


def infer_ok_count(score: int, num_batches: int) -> int:
    """Infer number of OK batches from score and total batch count.

    Score can be a percentage (0-100) or a raw count (<= num_batches).
    Heuristic: if score > num_batches, treat as percentage.
    """
    if score > num_batches:
        # Percentage
        return round(score / 100 * num_batches)
    else:
        # Raw count
        return score


def build_expectations(
    solutions: list[Solution], num_batches: int
) -> list[SolutionExpectation]:
    """Parse expectations from solution filenames."""
    expectations: list[SolutionExpectation] = []
    for sol in solutions:
        name = Path(sol.name).name
        lang = Langs.from_filename(name)
        batch_string = parse_batch_string(name)
        score = parse_score(name)
        verdict_tag = parse_verdict_tag(name)

        exp = SolutionExpectation(
            solution=sol,
            lang=lang,
            batch_string=batch_string,
            verdict_tag=verdict_tag,
            score=score,
        )

        if batch_string is not None:
            exp.positional = True
            if len(batch_string) != num_batches:
                warning(
                    f"{name}: batch string '{batch_string}' has {len(batch_string)} "
                    f"chars but there are {num_batches} batches"
                )
        elif score is not None:
            exp.expected_ok_count = infer_ok_count(score, num_batches)
            exp.positional = False
        else:
            warning(f"{name}: no batch string or score found, skipping for constraints")

        expectations.append(exp)
    return expectations


# ==================== Cache ====================

CACHE_FILENAME = ".findlimits_cache.json"


@dataclass
class SolutionTimingData:
    """Timing data collected for a single solution."""

    name: str
    lang: str  # Langs.Lang.value or "unknown"
    # batch_name -> max time in seconds across test cases in that batch
    # None means the solution TLE'd with the given cap
    batch_max_times: dict[str, Optional[float]]
    # batch_name -> status letter (O, W, T, E) observed when run
    batch_statuses: dict[str, str]
    # The timelimit cap used when running this solution
    timelimit_used: float


def load_cache(
    cache_path: Path,
) -> tuple[dict[str, SolutionTimingData], Optional[float]]:
    """Load cached timing data from file.

    Returns (cache_data, last_start_time).
    """
    if not cache_path.exists():
        return {}, None

    try:
        with open(cache_path, "r") as f:
            data = json.load(f)

        last_start = data.get("last_start") if isinstance(data, dict) else None

        # Handle old format where data was a list
        entries = data if isinstance(data, list) else data.get("entries", [])

        result = {}
        for entry in entries:
            td = SolutionTimingData(
                name=entry["name"],
                lang=entry["lang"],
                batch_max_times=entry["batch_max_times"],
                batch_statuses=entry["batch_statuses"],
                timelimit_used=entry["timelimit_used"],
            )
            result[td.name] = td
        return result, last_start
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        warning(f"Failed to load cache: {e!r}")
        return {}, None


def save_cache(
    cache_path: Path,
    data: dict[str, SolutionTimingData],
    last_start: float,
) -> None:
    """Save timing data to cache file with last_start timestamp."""
    entries = []
    for td in data.values():
        entries.append(
            {
                "name": td.name,
                "lang": td.lang,
                "batch_max_times": td.batch_max_times,
                "batch_statuses": td.batch_statuses,
                "timelimit_used": td.timelimit_used,
            }
        )
    with open(cache_path, "w") as f:
        json.dump({"last_start": last_start, "entries": entries}, f, indent=2)


# ==================== Execution ====================


def get_batches(inputs: Sequence[RelativePath]) -> list[str]:
    """Get sorted unique batch names from input files."""
    batches: set[str] = set()
    for inp in inputs:
        batch = Solution.parse_batch(inp)
        if "sample" not in batch:
            batches.add(batch)
    return sorted(batches, key=natural_sort_key)


def get_inputs_for_batch(
    inputs: Sequence[RelativePath], batch: str
) -> list[RelativePath]:
    """Get input files belonging to a specific batch."""
    return [inp for inp in inputs if Solution.parse_batch(inp) == batch]


def run_solution_on_inputs(
    sol: Solution,
    inputs: Sequence[RelativePath],
    indir: Directory,
    outdir: Directory,
    outext: str,
    tempext: str,
    checker: Optional[Checker],
    timelimit: timedelta,
    num_threads: int,
    only_batches: Optional[set[str]] = None,
    must_pass_batches: Optional[set[str]] = None,
    can_retry: bool = False,
) -> dict[str, list[tuple[Optional[list[timedelta]], Status]]]:
    """Run a single solution on all inputs with a given timelimit.

    Returns dict: batch_name -> [(run_times, status), ...] for each input in batch.

    If only_batches is provided, only runs inputs belonging to those batches.
    If must_pass_batches is provided and can_retry is True, a TLE on any of
    those batches triggers early abort: remaining queued tasks are skipped and
    running tasks in the TLE'd batch are killed. When can_retry is False
    (already at max timelimit), TLEs only kill same-batch siblings via
    cb_kill_siblings so other batches can finish for a complete picture.
    """
    # Set the timelimit for this solution's language
    lang = Langs.from_filename(Path(sol.name).name)
    Config.timelimits = {Langs.Lang.unknown: timelimit, lang: timelimit}
    Config.warn_timelimits = {Langs.Lang.unknown: timedelta(0)}

    # Reset solution statistics
    sol.statistics = Solution.Statistics(
        maxtime=timedelta(milliseconds=-1),
        sumtime=timedelta(),
        batchresults={},
        result=Status.ok,
        times=defaultdict(list),
        failedbatches=set(),
    )

    results: dict[str, list[tuple[Optional[list[timedelta]], Status]]] = defaultdict(
        list
    )

    # Abort event: set when a TLE occurs on a must_pass batch
    abort_event = threading.Event()

    parallel_logger_manager = ParallelLoggerManager()

    def logger_finalize(logger: BufferedLogger) -> None:
        logger.close()
        parallel_logger_manager.closed_event.set()

    tasks: list[TaskItem] = []
    for input_file in inputs:
        batch = Solution.parse_batch(input_file)
        if only_batches is not None and batch not in only_batches:
            continue
        ifile = indir / input_file
        prefix = str(outdir / input_file.with_suffix(""))
        ofile = Path(prefix + "." + outext)
        tfile = TempFile(prefix + ".fl." + tempext)

        logger = parallel_logger_manager.get_sink()

        def run_task(
            sol=sol,
            ifile=ifile,
            ofile=ofile,
            tfile=tfile,
            checker=checker,
            batch=batch,
            input_file=input_file,
            logger=logger,
            results=results,
        ):
            try:
                if abort_event.is_set():
                    # Already aborting — skip this task
                    results[batch].append((None, Status.tle))
                    return

                TASK_HISTORY.start(sol.name, batch, str(input_file))
                callbacks = TASK_HISTORY.get_callbacks(sol.name, batch, str(input_file))
                run_times, status = sol._run(
                    ifile, ofile, tfile, checker, False, logger, callbacks
                )

                # Clear warn-TLE flag since findlimits doesn't use warntimelimits
                if status == Status.ok and run_times is not None:
                    status = status.set_warntle(False)

                sol.record(ifile, status, run_times)
                sol.output_testcase_summary(ifile, status, run_times, logger)
                results[batch].append((run_times, status))

                # If TLE on a must_pass batch and retry is possible,
                # signal abort to skip remaining batches (they'll be
                # rerun at a higher cap anyway). If no retry is possible,
                # let other batches finish for a more complete picture.
                if (
                    status == Status.tle
                    and can_retry
                    and must_pass_batches is not None
                    and batch in must_pass_batches
                ):
                    abort_event.set()

                # Clean temp file
                if tfile.exists():
                    try:
                        Path(tfile).unlink()
                    except OSError:
                        pass
            except Exception as e:
                traceback.print_exc()
                logger.warning(repr(e))
                results[batch].append((None, Status.err))

        callbacks = [lambda _, logger=logger: logger_finalize(logger)]
        task_item = TaskItem(sol.name, batch, str(input_file), run_task, callbacks)
        tasks.append(task_item)

    queue = TaskQueue(tasks, TASK_HISTORY)

    with stylized_tqdm(desc=f"  {sol.name}", total=len(queue)) as progress_bar:
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            register_quit_with_executor(executor)

            def get_new_task(_=None):
                if abort_event.is_set():
                    # Drain remaining tasks from the queue (update progress)
                    while True:
                        task = queue.pop()
                        if task is None:
                            break
                        progress_bar.update()
                        for callback in task.callbacks:
                            callback(None)
                    return
                task = queue.pop()
                if task is None:
                    return
                task.callbacks.append(lambda _, p=progress_bar: p.update())
                try:
                    future = executor.submit(task.func)
                except RuntimeError:
                    for callback in task.callbacks:
                        callback(None)
                else:
                    for callback in task.callbacks:
                        future.add_done_callback(callback)
                    future.add_done_callback(get_new_task)

            for _ in range(num_threads):
                executor.submit(get_new_task)

            while parallel_logger_manager.last_open < len(
                parallel_logger_manager.sinks
            ):
                parallel_logger_manager.closed_event.wait()
                parallel_logger_manager.closed_event.clear()
                progress_bar.clear()
                plain(parallel_logger_manager.read_closed())
                progress_bar.display()

    default_logger.statistics += parallel_logger_manager.statistics
    return dict(results)


def collect_timing_data(
    sol: Solution,
    results: dict[str, list[tuple[Optional[list[timedelta]], Status]]],
    timelimit_used: float,
) -> SolutionTimingData:
    """Convert raw results into SolutionTimingData."""
    lang = Langs.from_filename(Path(sol.name).name)
    batch_max_times: dict[str, Optional[float]] = {}
    batch_statuses: dict[str, str] = {}

    for batch, batch_results in results.items():
        if "sample" in batch:
            continue
        times_in_batch = []
        batch_status = Status.ok
        for run_times, status in batch_results:
            if status == Status.tle:
                batch_status = Status.tle
            elif status != Status.ok and batch_status == Status.ok:
                batch_status = status

            if run_times is not None and len(run_times) > 0:
                times_in_batch.append(run_times[0].total_seconds())

        if batch_status == Status.tle:
            batch_max_times[batch] = None  # TLE - actual time unknown
        elif times_in_batch:
            batch_max_times[batch] = max(times_in_batch)
        else:
            batch_max_times[batch] = None

        batch_statuses[batch] = str(batch_status.set_warntle(False))[0]

    return SolutionTimingData(
        name=sol.name,
        lang=lang.value if lang != Langs.Lang.unknown else "unknown",
        batch_max_times=batch_max_times,
        batch_statuses=batch_statuses,
        timelimit_used=timelimit_used,
    )


def merge_timing_data(
    old: SolutionTimingData, new: SolutionTimingData
) -> SolutionTimingData:
    """Merge retry timing data into existing data.

    Keeps old data for batches not rerun, replaces with new data for
    batches that were rerun. Uses the higher timelimit_used (the retry cap).
    """
    merged_times = dict(old.batch_max_times)
    merged_statuses = dict(old.batch_statuses)
    for batch in new.batch_max_times:
        merged_times[batch] = new.batch_max_times[batch]
        merged_statuses[batch] = new.batch_statuses[batch]
    return SolutionTimingData(
        name=old.name,
        lang=old.lang,
        batch_max_times=merged_times,
        batch_statuses=merged_statuses,
        timelimit_used=max(old.timelimit_used, new.timelimit_used),
    )


def _robust_max(values: list[float], percentile: float = 75.0) -> float:
    """Return a robust estimate of the maximum, using a high percentile.

    Uses the given percentile (default P75) instead of the true max
    to protect against a single outlier dominating the cap.
    Falls back to the true max when there are fewer than 4 values
    (too few for percentile to help).
    """
    if not values:
        return 0.0
    if len(values) < 4:
        return max(values)
    s = sorted(values)
    idx = (len(s) - 1) * percentile / 100.0
    lo = int(idx)
    hi = lo + 1
    if hi >= len(s):
        return s[-1]
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def compute_timelimit_cap(
    sol: Solution,
    baseline_max_times: list[float],
    baseline_multiplier: float,
    max_timelimit: float,
) -> float:
    """Compute the timelimit cap for a solution based on baseline data.

    For the very first solutions (no baseline), use max_timelimit.
    Otherwise, use baseline_multiplier * _robust_max(baseline_max_times).

    baseline_max_times is a list of per-solution max-batch-times (each
    solution's slowest non-TLE batch). Uses P75 across solutions to
    protect against one unusually slow solution inflating caps.
    """
    if not baseline_max_times:
        return max_timelimit

    robust_baseline = _robust_max(baseline_max_times)
    cap = baseline_multiplier * robust_baseline
    # Don't go below a reasonable minimum or above max
    return max(0.1, min(cap, max_timelimit))


# ==================== Timelimit Computation ====================


@dataclass
class TimelimitConstraint:
    """A constraint on the timelimit from a single solution+batch."""

    solution_name: str
    batch: str
    # "must_pass" (timelimit > time, expects O),
    # "must_finish" (timelimit > time, expects W/E),
    # "must_tle" (timelimit < time)
    kind: str
    time: float  # The observed runtime (or cap if TLE)
    weight: float = 1.0  # For optimization when constraints conflict
    lower_bound: bool = (
        False  # True if time is only a lower bound (TLE'd, actual unknown)
    )


@dataclass
class TimelimitResult:
    """Result of timelimit computation for a single language."""

    lang: Langs.Lang
    recommended: Optional[float]  # Recommended timelimit in seconds
    valid_min: Optional[float]  # Minimum valid timelimit
    valid_max: Optional[float]  # Maximum valid timelimit
    all_satisfied: bool
    num_satisfied: int
    num_total: int
    constraints: list[TimelimitConstraint]
    unsatisfied: list[str]  # Descriptions of unsatisfied constraints


def compute_timelimit_for_language(
    lang: Langs.Lang,
    timing_data: dict[str, SolutionTimingData],
    expectations: list[SolutionExpectation],
    batches: list[str],
) -> TimelimitResult:
    """Compute optimal timelimit range for a single language."""

    # Gather constraints from all solutions of this language
    constraints: list[TimelimitConstraint] = []
    lang_expectations = [e for e in expectations if e.lang == lang]

    for exp in lang_expectations:
        td = timing_data.get(exp.solution.name)
        if td is None:
            continue

        if exp.positional and exp.batch_string is not None:
            # Positional expectations: each char maps to a batch
            for i, (batch, expected_char) in enumerate(zip(batches, exp.batch_string)):
                actual_time = td.batch_max_times.get(batch)
                actual_status = td.batch_statuses.get(batch, "?")

                if expected_char == "O":
                    # O: batch must pass (timelimit > actual_time)
                    if actual_status == "T":
                        # TLE'd but expected to finish — actual time unknown.
                        # Use cap as lower bound; this constraint cannot be
                        # meaningfully satisfied without retry.
                        constraints.append(
                            TimelimitConstraint(
                                exp.solution.name,
                                batch,
                                "must_pass",
                                td.timelimit_used,
                                lower_bound=True,
                            )
                        )
                    elif actual_status == "O" and actual_time is not None:
                        constraints.append(
                            TimelimitConstraint(
                                exp.solution.name, batch, "must_pass", actual_time
                            )
                        )
                elif expected_char in ("W", "E"):
                    # W/E: solution must have enough time to finish and
                    # produce wrong output (timelimit > actual_time)
                    if actual_status == "T":
                        # TLE'd but expected to finish — actual time unknown.
                        constraints.append(
                            TimelimitConstraint(
                                exp.solution.name,
                                batch,
                                "must_finish",
                                td.timelimit_used,
                                lower_bound=True,
                            )
                        )
                    elif actual_status in ("W", "E") and actual_time is not None:
                        constraints.append(
                            TimelimitConstraint(
                                exp.solution.name, batch, "must_finish", actual_time
                            )
                        )
                elif expected_char == "T":
                    # This batch must TLE: timelimit < actual_time
                    if actual_status in ("O", "W", "E") and actual_time is not None:
                        # Only add constraint if solution finished (O/W/E).
                        # WA/EXC means solution didn't produce correct output,
                        # which is also acceptable for "should TLE".
                        constraints.append(
                            TimelimitConstraint(
                                exp.solution.name, batch, "must_tle", actual_time
                            )
                        )
                    # If it TLE'd, constraint is satisfied for any timelimit <= cap

        elif exp.expected_ok_count is not None:
            # Non-positional: we know N batches should be OK
            # Only O vs T matters for determining which batches to TLE.
            # But W/E batches also need enough time to finish and produce
            # their wrong output, so they contribute must_pass constraints.
            batch_times = []
            for batch in batches:
                t = td.batch_max_times.get(batch)
                s = td.batch_statuses.get(batch, "?")
                batch_times.append((batch, t, s))

            # Batches that finished (OK or WA/EXC) with known times
            ok_batches_observed = [
                (b, t, s) for b, t, s in batch_times if s == "O" and t is not None
            ]
            wa_batches_observed = [
                (b, t, s)
                for b, t, s in batch_times
                if s in ("W", "E") and t is not None
            ]

            num_ok = exp.expected_ok_count
            num_ok_observed = len(ok_batches_observed)

            # Sort OK batches by time (ascending)
            ok_batches_observed.sort(key=lambda x: x[1])

            # WA/EXC batches: don't need constraints. We can't be sure if
            # they should have been TLE'd or not without positional info.

            # For OK batches: determine which should remain OK vs become TLE
            if exp.verdict_tag in ("WA", "EXC"):
                # WA/EXC-tagged solutions: score mismatch from accidentally-
                # correct batches is not fixable via timelimit. Only generate
                # must_pass so they have time to finish; never must_tle.
                for batch, t, _s in ok_batches_observed:
                    constraints.append(
                        TimelimitConstraint(exp.solution.name, batch, "must_pass", t)
                    )
            elif num_ok_observed <= num_ok:
                # All OK batches should remain OK (must_pass)
                for batch, t, _s in ok_batches_observed:
                    constraints.append(
                        TimelimitConstraint(exp.solution.name, batch, "must_pass", t)
                    )
            else:
                # Some currently-OK batches need to become TLE.
                # Constraint: we can only TLE OK batches whose time is
                # strictly above the max WA/EXC time, because any timelimit
                # that would TLE a faster OK batch would also TLE slower
                # WA/EXC batches (preventing them from producing their
                # wrong output).
                max_wa_time = (
                    max(t for _b, t, _s in wa_batches_observed)
                    if wa_batches_observed
                    else 0.0
                )

                # Split OK batches into those that CAN be TLE'd (above
                # max WA time) and those that CANNOT.
                tle_eligible = [
                    (b, t, s) for b, t, s in ok_batches_observed if t > max_wa_time
                ]
                tle_ineligible = [
                    (b, t, s) for b, t, s in ok_batches_observed if t <= max_wa_time
                ]

                num_to_tle = num_ok_observed - num_ok
                num_can_tle = len(tle_eligible)

                if num_can_tle >= num_to_tle:
                    # Enough eligible batches: TLE the slowest eligible ones
                    # (they are farthest from the boundary and easiest to
                    # TLE), keep the rest as must_pass. All ineligible are
                    # must_pass.
                    # tle_eligible is already sorted ascending (subset of
                    # ok_batches_observed which was sorted).
                    must_pass_from_eligible = tle_eligible[: num_can_tle - num_to_tle]
                    must_tle_list = tle_eligible[num_can_tle - num_to_tle :]
                    must_pass_list = tle_ineligible + must_pass_from_eligible
                else:
                    # Not enough eligible batches above WA time. TLE all
                    # eligible ones. The remaining needed TLEs come from
                    # the slowest ineligible batches, which will create
                    # inherent conflicts with WA must_pass constraints.
                    must_tle_list = list(tle_eligible)
                    remaining = num_to_tle - num_can_tle
                    # From ineligible, TLE the slowest ones (end of sorted
                    # list). These will conflict with WA must_pass.
                    must_tle_from_ineligible = tle_ineligible[-remaining:]
                    must_pass_from_ineligible = tle_ineligible[:-remaining]
                    must_tle_list.extend(must_tle_from_ineligible)
                    must_pass_list = must_pass_from_ineligible

                for batch, t, _s in must_pass_list:
                    constraints.append(
                        TimelimitConstraint(exp.solution.name, batch, "must_pass", t)
                    )
                for batch, t, _s in must_tle_list:
                    constraints.append(
                        TimelimitConstraint(exp.solution.name, batch, "must_tle", t)
                    )

    if not constraints:
        return TimelimitResult(
            lang=lang,
            recommended=None,
            valid_min=None,
            valid_max=None,
            all_satisfied=True,
            num_satisfied=0,
            num_total=0,
            constraints=[],
            unsatisfied=["No timing constraints found"],
        )

    # Compute valid range (exclude lower_bound constraints — their times are
    # only lower bounds, so they shouldn't tighten valid_min beyond what we
    # actually know).
    must_pass_times = [
        c.time for c in constraints if c.kind == "must_pass" and not c.lower_bound
    ]
    must_tle_times = [c.time for c in constraints if c.kind == "must_tle"]
    lower_bound_constraints = [c for c in constraints if c.lower_bound]

    valid_min = max(must_pass_times) if must_pass_times else 0.0
    valid_max = min(must_tle_times) if must_tle_times else float("inf")

    unsatisfied: list[str]
    if valid_min < valid_max and not lower_bound_constraints:
        # Valid range exists and no uncertain constraints
        if valid_max == float("inf"):
            recommended = valid_min * 1.5
        else:
            recommended = math.sqrt(valid_min * valid_max)
        all_satisfied = True
        num_satisfied = len(constraints)
        unsatisfied = []
    else:
        # No valid range, or some constraints have unknown actual times.
        # Find best compromise considering all constraints.
        if valid_min < valid_max:
            # Range exists but we have lower_bound constraints
            if valid_max == float("inf"):
                recommended = valid_min * 1.5
            else:
                recommended = math.sqrt(valid_min * valid_max)
        else:
            recommended = None  # will be set by _find_best_compromise

        recommended, num_satisfied, unsatisfied = _find_best_compromise(
            constraints, valid_min, valid_max, recommended
        )
        all_satisfied = num_satisfied == len(constraints)

    return TimelimitResult(
        lang=lang,
        recommended=recommended,
        valid_min=valid_min if must_pass_times else None,
        valid_max=valid_max if must_tle_times and valid_max != float("inf") else None,
        all_satisfied=all_satisfied,
        num_satisfied=num_satisfied,
        num_total=len(constraints),
        constraints=constraints,
        unsatisfied=unsatisfied,
    )


def _find_best_compromise(
    constraints: list[TimelimitConstraint],
    valid_min: float,
    valid_max: float,
    hint: Optional[float] = None,
) -> tuple[float, int, list[str]]:
    """When no valid timelimit exists, find the one that satisfies most constraints.

    lower_bound constraints (from TLE'd batches with unknown actual runtime)
    are always counted as unsatisfied, since we don't know the actual time.
    """
    # Collect all boundary times as candidate timelimits
    candidates: set[float] = set()
    for c in constraints:
        candidates.add(c.time - 0.001)
        candidates.add(c.time + 0.001)
        candidates.add(c.time)
    if hint is not None and hint > 0:
        candidates.add(hint)

    best_tl = 0.0
    best_satisfied = -1
    best_unsatisfied: list[str] = []

    for tl in sorted(candidates):
        if tl <= 0:
            continue
        satisfied = 0
        unsatisfied = []
        for c in constraints:
            if c.lower_bound:
                # Actual time unknown — always unsatisfied
                if c.kind == "must_pass":
                    expected_str = "pass"
                elif c.kind == "must_finish":
                    expected_str = "finish"
                else:
                    expected_str = "TLE"
                unsatisfied.append(
                    f"  {c.solution_name} batch {c.batch}: "
                    f"expected {expected_str}, time>={c.time:.3f}s (TLE, needs rerun), "
                    f"timelimit={tl:.3f}s"
                )
            elif c.kind in ("must_pass", "must_finish") and tl > c.time:
                satisfied += 1
            elif c.kind == "must_tle" and tl < c.time:
                satisfied += 1
            else:
                if c.kind == "must_pass":
                    expected_str = "pass"
                elif c.kind == "must_finish":
                    expected_str = "finish"
                else:
                    expected_str = "TLE"
                unsatisfied.append(
                    f"  {c.solution_name} batch {c.batch}: "
                    f"expected {expected_str}, "
                    f"time={c.time:.3f}s, timelimit={tl:.3f}s"
                )
        if satisfied > best_satisfied:
            best_satisfied = satisfied
            best_tl = tl
            best_unsatisfied = unsatisfied

    return best_tl, best_satisfied, best_unsatisfied


# ==================== Retry Logic ====================


def get_must_pass_batches(
    exp: Optional[SolutionExpectation], batches: list[str]
) -> Optional[set[str]]:
    """Get the set of batches that must pass (not TLE) for a given expectation.

    For positional expectations: batches with O/W/E must pass.
    For non-positional: we don't know which specific batches need to pass,
    so we can't do early abort (return None).
    Returns None if no expectation is available (no abort logic).
    """
    if exp is None:
        return None
    if exp.positional and exp.batch_string is not None:
        result: set[str] = set()
        for batch, expected_char in zip(batches, exp.batch_string):
            if expected_char in ("O", "W", "E"):
                result.add(batch)
        return result if result else None
    return None


def find_solutions_needing_retry(
    timing_data: dict[str, SolutionTimingData],
    expectations: list[SolutionExpectation],
    batches: list[str],
) -> list[tuple[SolutionExpectation, list[str]]]:
    """Find solutions that TLE'd on batches they were expected to pass.

    Returns list of (expectation, [batch_names]) for solutions that need retry.
    Only includes solutions where TLE prevents satisfying the expectation:
    - Positional: expected O/W/E but got TLE
    - Non-positional: not enough non-TLE batches to meet expected_ok_count
    """
    needs_retry: list[tuple[SolutionExpectation, list[str]]] = []

    for exp in expectations:
        td = timing_data.get(exp.solution.name)
        if td is None:
            continue

        tle_batches: list[str] = []

        if exp.positional and exp.batch_string is not None:
            for batch, expected_char in zip(batches, exp.batch_string):
                if expected_char in ("O", "W", "E"):
                    actual_status = td.batch_statuses.get(batch, "?")
                    if actual_status == "T":
                        tle_batches.append(batch)
        elif exp.expected_ok_count is not None:
            # Non-positional: count how many batches passed vs expected.
            # Only retry if the number of OK batches is LESS than expected,
            # meaning some TLE'd batches need to pass for the expectation
            # to be met. If we already have enough OK batches, the TLEs
            # are acceptable (they might be the ones we want to TLE).
            num_ok_or_wa = 0
            all_tle_batches: list[str] = []
            for batch in batches:
                s = td.batch_statuses.get(batch, "?")
                if s in ("O", "W", "E"):
                    num_ok_or_wa += 1
                elif s == "T":
                    all_tle_batches.append(batch)

            if num_ok_or_wa < exp.expected_ok_count:
                # Not enough batches passed — retry all TLE'd ones
                tle_batches = all_tle_batches

        if tle_batches:
            needs_retry.append((exp, tle_batches))

    return needs_retry


def compute_retry_cap(
    prev_cap: float,
    max_timelimit: float,
    retry_multiplier: float = 3.0,
) -> float:
    """Compute the retry cap for a solution that TLE'd.

    Strategy: progressively increase from the previous cap by retry_multiplier.
    If the result is close to max_timelimit (i.e., one more partial step
    would reach it: cap * multiplier^(1/4) >= max_timelimit), round up
    to max_timelimit directly to avoid wasting an iteration.
    """
    cap = prev_cap * retry_multiplier

    # Round up: if we're close enough to max that a fractional step
    # would reach it, just go to max directly.
    if prev_cap * retry_multiplier**0.25 >= max_timelimit:
        cap = max_timelimit

    return max(0.1, min(cap, max_timelimit))


# ==================== Phase 3: Robustness Verification ====================


def find_must_tle_needing_verification(
    timing_data: dict[str, SolutionTimingData],
    expectations: list[SolutionExpectation],
    batches: list[str],
    recommended_tl: float,
    closeness_ratio: float = 3.0,
) -> list[tuple[SolutionExpectation, list[str]]]:
    """Find must-TLE batches that TLE'd at caps too close to recommended TL.

    A must-TLE batch that TLE'd at cap X is guaranteed to TLE at any TL <= X.
    But if X is close to recommended_tl, we can't be sure the batch wouldn't
    finish at X + epsilon (which might be above or below recommended_tl).

    "Close" means: cap / recommended_tl < closeness_ratio. If the batch
    TLE'd at 10x the recommended TL, there's no concern.

    Returns list of (expectation, [batch_names]) to rerun at higher caps.
    Only considers positional expectations with explicit 'T' chars.
    """
    needs_verification: list[tuple[SolutionExpectation, list[str]]] = []

    for exp in expectations:
        td = timing_data.get(exp.solution.name)
        if td is None:
            continue

        uncertain_batches: list[str] = []

        if exp.positional and exp.batch_string is not None:
            for batch, expected_char in zip(batches, exp.batch_string):
                if expected_char != "T":
                    continue
                actual_status = td.batch_statuses.get(batch, "?")
                actual_time = td.batch_max_times.get(batch)
                if actual_status == "T" and actual_time is None:
                    # TLE'd — cap was td.timelimit_used.
                    # Check if this is close to recommended TL.
                    if td.timelimit_used < recommended_tl * closeness_ratio:
                        uncertain_batches.append(batch)

        if uncertain_batches:
            needs_verification.append((exp, uncertain_batches))

    return needs_verification


def valid_range_gap(tl_result: TimelimitResult) -> float:
    """Compute the ratio between valid_max and valid_min.

    Returns inf if either bound is None (open-ended range).
    """
    if tl_result.valid_min is None or tl_result.valid_max is None:
        return float("inf")
    if tl_result.valid_min <= 0:
        return float("inf")
    return tl_result.valid_max / tl_result.valid_min


# ==================== Output Presentation ====================


def format_time(t: Optional[float]) -> str:
    """Format time in seconds to a readable string."""
    if t is None:
        return "  TLE  "
    if t < 0.001:
        return f"{t * 1000:5.1f}ms"
    return f"{t:6.3f}s"


def print_expectations(
    expectations: list[SolutionExpectation], batches: list[str]
) -> None:
    """Print parsed expectations for all solutions."""
    infob("\n===== Parsed Expectations =====")
    name_width = max(len(Path(e.solution.name).name) for e in expectations)
    for exp in expectations:
        name = Path(exp.solution.name).name
        lang_str = exp.lang.name if exp.lang != Langs.Lang.unknown else "?"
        if exp.positional and exp.batch_string:
            exp_str = exp.batch_string
        elif exp.expected_ok_count is not None:
            exp_str = f"({exp.expected_ok_count}/{len(batches)} OK)"
        else:
            exp_str = "(no expectation)"
        tag_str = f" [{exp.verdict_tag}]" if exp.verdict_tag else ""
        info(f"  {name:{name_width}}  {lang_str:>6}  {exp_str}{tag_str}")


def compute_solution_margins(
    td: SolutionTimingData,
    batches: list[str],
    recommended_tl: float,
) -> tuple[Optional[float], Optional[float]]:
    """Compute headroom and missing margins for a single solution.

    Headroom: recommended_TL / max(batch times that pass at recommended_TL).
    How much faster the solution runs than the timelimit.
    E.g., 3.1x means the solution is 3.1x faster than the limit.

    Missing: time_of_next_batch / recommended_TL.
    How much slower the solution would need to be to lose one more batch.
    E.g., 2.0x means the next harder batch takes 2x the timelimit.

    Returns (headroom, missing) where None means not computable.
    """
    # Get all batch times that are known (not TLE)
    batch_times: list[tuple[str, float]] = []
    for batch in batches:
        t = td.batch_max_times.get(batch)
        if t is not None:
            batch_times.append((batch, t))

    if not batch_times:
        return None, None

    # Sort by time
    batch_times.sort(key=lambda x: x[1])

    # Find how many pass at recommended_tl
    pass_count = sum(1 for _, t in batch_times if t <= recommended_tl)

    if pass_count == 0:
        headroom = None
    else:
        # Headroom = recommended / max time of passing batches
        max_pass_time = max(t for _, t in batch_times[:pass_count])
        if max_pass_time > 0:
            headroom = recommended_tl / max_pass_time
        else:
            headroom = None

    # Missing = time of next batch / recommended
    if pass_count < len(batch_times):
        next_batch_time = batch_times[pass_count][1]
        missing = next_batch_time / recommended_tl
    else:
        missing = None

    return headroom, missing


def compute_outcome_at_timelimit_non_positional(
    td: SolutionTimingData,
    batches: list[str],
    timelimit: float,
) -> str:
    """Compute batch outcome string for non-positional expectations.

    Preserves the actual status (O, W, E) but changes it to T if the batch
    would exceed the timelimit. TLE'd batches always remain T.
    Output is in the original batch order.
    """
    result = []

    for batch in batches:
        t = td.batch_max_times.get(batch)
        s = td.batch_statuses.get(batch, "?")

        if s == "T":
            # TLE'd at original cap - would also TLE at any lower timelimit
            result.append("T")
        elif t is not None:
            # Has actual time - check if it fits in timelimit
            if t <= timelimit:
                result.append(s)  # Keep original status (O, W, E)
            else:
                result.append("T")
        else:
            # Unknown status - skip
            result.append("?")

    return "".join(result)

    return "".join(result)


def compute_batch_outcome_at_timelimit(
    td: SolutionTimingData,
    batches: list[str],
    timelimit: float,
) -> str:
    """Compute what the batch outcomes would be at a given timelimit.

    For each batch:
    - If we have an actual time and it's <= timelimit: O
    - If we have an actual time and it's > timelimit: T
    - If the batch TLE'd at the original cap (no actual time):
      - We know it exceeded the cap (> timelimit_used), which is > timelimit
      - So it would also TLE at any lower timelimit: T
    """
    result = []
    for batch in batches:
        t = td.batch_max_times.get(batch)
        s = td.batch_statuses.get(batch)
        if t is not None:
            result.append(s if t <= timelimit else "T")
        else:
            # TLE'd at original cap, so it definitely exceeds timelimit too
            result.append("T")
    return "".join(result)


def highlight_differences(expected: str, actual: str) -> str:
    """Highlight characters that differ between expected and actual.

    Uses ANSI escape codes to highlight differences in yellow bold.
    """
    if len(expected) != len(actual):
        return actual

    result = []
    for e, a in zip(expected, actual):
        if e != a:
            result.append(f"\033[1;33m{a}\033[0m")  # yellow bold
        else:
            result.append(a)
    return "".join(result)


def print_timing_table(
    timing_data: dict[str, SolutionTimingData],
    expectations: list[SolutionExpectation],
    batches: list[str],
    tl_results: Optional[dict[Langs.Lang, TimelimitResult]] = None,
) -> None:
    """Print detailed timing table for all solutions."""
    infob("\n===== Timing Data =====")

    # Check if we can show with-recommended column
    show_with_recommended = tl_results is not None and any(
        r.recommended is not None for r in tl_results.values()
    )

    # Header
    name_width = max(
        len(Path(e.solution.name).name)
        for e in expectations
        if e.solution.name in timing_data
    )
    name_width = max(name_width, 8)
    batch_header = "  ".join(f"{'B' + b:>7}" for b in batches)

    if show_with_recommended:
        info(
            f"  {'Solution':{name_width}}  {'Lang':>6}  {batch_header}"
            f"  Encountered  Expected  W/Recomm  Headroom  Missing"
        )
        info(
            f"  {'-' * name_width}  {'-' * 6}  "
            f"{'  '.join(['-' * 7] * len(batches))}"
            f"  -----------  --------  --------  --------  -------"
        )
    else:
        info(
            f"  {'Solution':{name_width}}  {'Lang':>6}  {batch_header}"
            f"  Encountered  Expected  Headroom  Missing"
        )
        info(
            f"  {'-' * name_width}  {'-' * 6}  "
            f"{'  '.join(['-' * 7] * len(batches))}"
            f"  -----------  --------  --------  -------"
        )

    for exp in expectations:
        td = timing_data.get(exp.solution.name)
        if td is None:
            continue
        name = Path(exp.solution.name).name
        lang_str = exp.lang.name if exp.lang != Langs.Lang.unknown else "?"

        # Per-batch times
        time_cells = []
        for batch in batches:
            t = td.batch_max_times.get(batch)
            time_cells.append(format_time(t))
        times_str = "  ".join(time_cells)

        # Expected batch string
        if exp.positional and exp.batch_string:
            exp_str = exp.batch_string
        elif exp.expected_ok_count is not None:
            exp_str = f"({exp.expected_ok_count} OK)"
        else:
            exp_str = "  -   "

        # Encountered batch string (actual result at cap used)
        encountered_chars = []
        for batch in batches:
            s = td.batch_statuses.get(batch, "?")
            encountered_chars.append(s)
        encountered_str = "".join(encountered_chars)

        # Compute margins
        headroom, missing = None, None
        if tl_results is not None:
            tl_result = tl_results.get(exp.lang)
            if tl_result is not None and tl_result.recommended is not None:
                headroom, missing = compute_solution_margins(
                    td, batches, tl_result.recommended
                )
        hr_str = f"{headroom:.1f}x" if headroom is not None else "-  "
        ms_str = f"{missing:.1f}x" if missing is not None else "-  "
        margin_str = f"{hr_str:>8}  {ms_str:>7}"

        # With Recommended: what would happen at recommended TL
        with_recommended_str = ""
        if show_with_recommended and tl_results is not None:
            tl_result = tl_results.get(exp.lang)
            if tl_result is not None and tl_result.recommended is not None:
                # Compute with-recommended outcome
                if exp.positional and exp.batch_string:
                    with_recommended_str = compute_batch_outcome_at_timelimit(
                        td, batches, tl_result.recommended
                    )
                    # Highlight differences from expected
                    if with_recommended_str != exp.batch_string:
                        a, b = exp.batch_string, with_recommended_str
                        with_recommended_str = highlight_differences(a, b)
                        exp_str = highlight_differences(b, a)
                elif exp.expected_ok_count is not None:
                    # Non-positional: compute outcome string at recommended TL
                    with_recommended_str = compute_outcome_at_timelimit_non_positional(
                        td, batches, tl_result.recommended
                    )
                else:
                    with_recommended_str = "(-)"

        if show_with_recommended:
            # Pad columns accounting for ANSI escape codes
            encountered_padded = f"{encountered_str:<11}"
            exp_padded = " " * (8 - len(strip_ansi(exp_str))) + exp_str
            # For with_recommended, calculate display width (strip ANSI)
            with_padded = with_recommended_str + " " * (
                8 - len(strip_ansi(with_recommended_str))
            )

            info(
                f"  {name:{name_width}}  {lang_str:>6}  {times_str}"
                f"  {encountered_padded}  {exp_padded}  {with_padded}  {margin_str}"
            )
        else:
            info(
                f"  {name:{name_width}}  {lang_str:>6}  {times_str}"
                f"  {encountered_str:<11}  {exp_str:>8}  {margin_str}"
            )


def print_results(
    results: dict[Langs.Lang, TimelimitResult], batches: list[str]
) -> None:
    """Print timelimit computation results."""
    infob("\n===== Findlimits Results =====")

    for lang, result in results.items():
        lang_name = lang.name
        info(f"\n  Language: {lang_name}")

        if result.recommended is not None:
            info(f"    Recommended timelimit: {result.recommended:.2f}s")
        else:
            info("    Recommended timelimit: (no data)")
            continue

        if result.valid_min is not None and result.valid_max is not None:
            if result.valid_min < result.valid_max:
                info(
                    f"    Valid range: [{result.valid_min:.3f}s, {result.valid_max:.3f}s]"
                )
            else:
                warning(
                    f"    Conflicting range: [{result.valid_min:.3f}s, {result.valid_max:.3f}s] "
                    f"(min > max, no valid timelimit exists)"
                )
        elif result.valid_min is not None:
            info(f"    Valid range: [{result.valid_min:.3f}s, +inf)")
        elif result.valid_max is not None:
            info(f"    Valid range: (0, {result.valid_max:.3f}s]")

        if result.all_satisfied:
            info(f"    All {result.num_total} constraints satisfied.")
        else:
            info(
                f"    {result.num_satisfied}/{result.num_total} constraints satisfied."
            )
            for msg in result.unsatisfied:
                warning(msg)

    # Print ratios between languages
    lang_results = {lang: r for lang, r in results.items() if r.recommended is not None}
    if len(lang_results) > 1:
        langs = sorted(lang_results.keys(), key=lambda lang: lang.name)
        infob("\n  Language ratios:")
        base_lang = langs[0]
        base_tl = lang_results[base_lang].recommended
        for lang in langs[1:]:
            tl = lang_results[lang].recommended
            if base_tl and tl:
                ratio = tl / base_tl
                info(f"    {lang.name}/{base_lang.name} = {ratio:.2f}x")

    # Print recommended -t flag
    if lang_results:
        parts = []
        for lang in sorted(lang_results.keys(), key=lambda lang: lang.name):
            r = lang_results[lang]
            if r.recommended is not None:
                ext = Langs.ext[lang][0] if Langs.ext[lang] else lang.name
                parts.append(f"{ext}={r.recommended:.1f}")
        if parts:
            infob(f"\n  Recommended -t flag: {','.join(parts)}")


def print_warnings(
    timing_data: dict[str, SolutionTimingData],
    expectations: list[SolutionExpectation],
    batches: list[str],
    results: dict[Langs.Lang, TimelimitResult],
) -> None:
    """Print warnings about mismatches between expectations and reality."""
    for exp in expectations:
        td = timing_data.get(exp.solution.name)
        if td is None:
            continue
        name = Path(exp.solution.name).name
        result = results.get(exp.lang)
        if result is None or result.recommended is None:
            continue

        recommended_tl = result.recommended

        if exp.positional and exp.batch_string:
            for i, (batch, expected_char) in enumerate(zip(batches, exp.batch_string)):
                actual_status = td.batch_statuses.get(batch, "?")
                actual_time = td.batch_max_times.get(batch)

                # Check if actual non-TLE status matches expectation
                if expected_char in ("W", "E") and actual_status not in ("W", "E"):
                    if actual_status == "O":
                        warning(
                            f"{name} batch {batch}: expected {expected_char} "
                            f"but got OK (time={format_time(actual_time).strip()})"
                        )
                    elif actual_status == "T":
                        warning(
                            f"{name} batch {batch}: expected {expected_char} "
                            f"but got TLE"
                        )
                elif expected_char == "O" and actual_status not in ("O", "T"):
                    warning(
                        f"{name} batch {batch}: expected OK but got {actual_status} "
                        f"(time={format_time(actual_time).strip()})"
                    )

        elif exp.expected_ok_count is not None:
            # Score-based: check if the actual score matches at the recommended TL
            num_would_pass = 0
            num_wa = 0
            for batch in batches:
                s = td.batch_statuses.get(batch, "?")
                t = td.batch_max_times.get(batch)
                if s == "O" and t is not None and t <= recommended_tl:
                    num_would_pass += 1
                elif s in ("W", "E"):
                    num_wa += 1

            if num_would_pass != exp.expected_ok_count:
                warning(
                    f"{name}: expected {exp.expected_ok_count} OK batches "
                    f"but would get {num_would_pass} at timelimit "
                    f"{recommended_tl:.2f}s"
                    + (f" ({num_wa} WA/EXC)" if num_wa > 0 else "")
                )

        # Warn if verdict tag doesn't match observations
        if exp.verdict_tag == "TLE":
            has_tle = False
            for b in batches:
                if td.batch_statuses.get(b) == "T":
                    has_tle = True
                    break
                bt = td.batch_max_times.get(b)
                if bt is not None and bt > recommended_tl:
                    has_tle = True
                    break
            if not has_tle:
                warning(
                    f"{name}: filename contains TLE tag but no batch appears "
                    f"to TLE at recommended timelimit {recommended_tl:.2f}s"
                )


# ==================== Main Flow ====================


def run(args: ArgsFindlimits) -> None:
    setup_config(
        args,
        ("progdir", "pythoncmd", "memorylimit", "quiet", "compile", "execute"),
    )
    Config.rus_time = False
    Config.fail_skip = True
    Config.threads = args.threads if args.threads else Config.get_cpu_corecount(0.25)

    os.system(f"{Config.os_config.cmd_python} --version")

    # Discover programs
    files = get_relevant_prog_files_deeper(args.programs)
    solutions_raw, checker_files = create_programs_from_files(files, True)

    # Filter to only Solutions (not Validators)
    solutions: list[Solution] = [
        s
        for s in solutions_raw
        if isinstance(s, Solution) and not isinstance(s, Validator)
    ]

    if not solutions:
        fatal("No solutions found")

    # Set up checker
    checker: Optional[Checker] = None
    if checker_files:
        checker = Checker(str(checker_files[0]), False)
    elif args.diffcmd:
        checker = Checker(args.diffcmd, False)
    else:
        checker = Checker("diff", False)

    # Sort solutions: fastest first (highest score first via compare_mask)
    solutions.sort(reverse=True, key=lambda s: s.compare_mask())

    # Prepare programs (compile)
    programs_to_prepare: list = solutions[:]
    if checker is not None:
        programs_to_prepare.append(checker)
    prepare_programs(programs_to_prepare, max(4, Config.threads))

    # Deduplicate after compilation
    solutions_deduped = deduplicate_solutions(solutions)
    solutions = [
        s
        for s in solutions_deduped
        if isinstance(s, Solution) and not isinstance(s, Validator)
    ]

    # Collect source/executable paths that were compiled (for cache invalidation)
    source_mtimes: dict[str, float] = {}
    for sol in solutions:
        # Check if source is newer than cache (for interpreted languages)
        if sol.source_path and sol.source_path.exists():
            source_mtimes[sol.name] = sol.source_path.stat().st_mtime
        # Check if executable is newer than cache (for compiled languages)
        if sol.executable_path and sol.executable_path.exists():
            # Use whichever is newer
            exe_mtime = sol.executable_path.stat().st_mtime
            if sol.name in source_mtimes:
                source_mtimes[sol.name] = max(source_mtimes[sol.name], exe_mtime)
            else:
                source_mtimes[sol.name] = exe_mtime

    # Set display config
    for s in solutions:
        Config.cmd_maxlen = max(Config.cmd_maxlen, len(s.name))
    Config.inside_oneline = True

    # Discover inputs
    if not args.indir.exists():
        fatal(f"Input directory `{args.indir}` doesn't exist.")
    inputs = sorted_files_with_ext(
        args.indir, args.inext, lambda p: natural_sort_key(str(p))
    )
    if not inputs:
        fatal("No input files found")

    Config.inside_inputmaxlen = max(len(str(p)) for p in inputs)

    # Pre-signal checker output_ready for all inputs, since outputs already exist
    # (findlimits doesn't generate outputs; it only checks correctness)
    if checker is not None:
        for inp in inputs:
            ifile = args.indir / inp
            checker.output_ready[ifile].set()

    batches = get_batches(inputs)
    num_batches = len(batches)
    infob(f"Found {len(inputs)} inputs in {num_batches} batches: {', '.join(batches)}")
    infob(f"Found {len(solutions)} solutions")

    # Parse expectations
    expectations = build_expectations(solutions, num_batches)
    print_expectations(expectations, batches)

    # Load cache first (before we know source_mtimes)
    cache_path = Path(args.outdir) / CACHE_FILENAME
    cached_data, last_start = load_cache(cache_path)
    if cached_data:
        infob(f"\nLoaded {len(cached_data)} cached results from {cache_path}")

    # Invalidate cache entries where source was modified after last_start
    if last_start is not None:
        stale_entries = [
            name
            for name, td in cached_data.items()
            if source_mtimes.get(name, 0) > last_start
        ]
        for name in stale_entries:
            del cached_data[name]
        if stale_entries:
            infob(f"  Invalidated {len(stale_entries)} stale cache entries")

    # Record new start time (will be saved to cache)
    current_start = time.time()
    save_cache(cache_path, cached_data, current_start)

    # === Adaptive execution with integrated retry ===
    infob("\n===== Running Solutions =====")

    # Baseline: per-language list of per-solution max-batch-times.
    # Each solution contributes one value: its slowest non-TLE batch time.
    # P75 across solutions protects against outlier solutions inflating caps.
    baseline_max_times: dict[Langs.Lang, list[float]] = defaultdict(list)
    timing_data: dict[str, SolutionTimingData] = {}

    # Build a lookup from solution name to expectation for retry logic
    exp_by_name: dict[str, SolutionExpectation] = {
        exp.solution.name: exp for exp in expectations
    }

    # Pre-populate baselines from cache
    for td in cached_data.values():
        lang = Langs.Lang(td.lang) if td.lang != "unknown" else Langs.Lang.unknown
        non_tle_times = [t for t in td.batch_max_times.values() if t is not None]
        if non_tle_times:
            baseline_max_times[lang].append(max(non_tle_times))

    for sol in solutions:
        name = Path(sol.name).name
        lang = Langs.from_filename(name)
        exp = exp_by_name.get(sol.name)

        # Check cache: reuse if data is complete or cap was sufficient.
        # Complete data = all batches have actual times (no TLEs), so a
        # higher cap would not reveal anything new.
        cap = compute_timelimit_cap(
            sol,
            baseline_max_times.get(lang, []),
            args.baseline_multiplier,
            args.max_timelimit,
        )
        used_cache = False
        if sol.name in cached_data:
            td = cached_data[sol.name]
            all_complete = all(t is not None for t in td.batch_max_times.values())
            if all_complete or td.timelimit_used >= cap:
                infob(f"  Using cached data for {name}")
                timing_data[sol.name] = td
                used_cache = True
            else:
                infob(
                    f"  Cache stale for {name} "
                    f"(cached cap={td.timelimit_used:.2f}s < needed={cap:.2f}s)"
                )

        if not used_cache:
            infob(f"\n  Running {name} (cap={cap:.2f}s)")

            # Compute must_pass_batches for early abort on unexpected TLE
            must_pass = get_must_pass_batches(exp, batches)

            # Run solution on all inputs
            results = run_solution_on_inputs(
                sol,
                inputs,
                args.indir,
                args.outdir,
                args.outext,
                args.tempext,
                checker,
                timedelta(seconds=cap),
                Config.threads,
                must_pass_batches=must_pass,
                can_retry=cap < args.max_timelimit,
            )

            # Collect timing data
            td = collect_timing_data(sol, results, cap)
            timing_data[sol.name] = td

            # Save cache incrementally
            cached_data[sol.name] = td
            save_cache(cache_path, cached_data, current_start)

        # === Integrated retry: retry this solution if it has TLE on must-pass
        # batches (works for both freshly-run and cache-loaded data) ===
        if exp is not None:
            while True:
                retry_needed = find_solutions_needing_retry(timing_data, [exp], batches)
                if not retry_needed:
                    break

                _, tle_batches = retry_needed[0]
                prev_cap = timing_data[sol.name].timelimit_used
                retry_cap = compute_retry_cap(prev_cap, args.max_timelimit)

                if retry_cap <= prev_cap:
                    if used_cache:
                        # Cache had TLE at max cap — nothing more we can do
                        warning(
                            f"  {name}: cached at max cap "
                            f"({prev_cap:.2f}s), still has TLE on "
                            f"batches: {', '.join(tle_batches)}"
                        )
                    else:
                        warning(
                            f"  {name}: already at max cap "
                            f"({prev_cap:.2f}s), cannot retry higher"
                        )
                    break

                infob(
                    f"  Retrying {name} (cap={retry_cap:.2f}s, "
                    f"was={prev_cap:.2f}s, "
                    f"TLE batches: {', '.join(tle_batches)})"
                )

                # Only rerun the TLE'd batches (all are must-pass)
                tle_batch_set = set(tle_batches)
                retry_results = run_solution_on_inputs(
                    sol,
                    inputs,
                    args.indir,
                    args.outdir,
                    args.outext,
                    args.tempext,
                    checker,
                    timedelta(seconds=retry_cap),
                    Config.threads,
                    only_batches=tle_batch_set,
                    must_pass_batches=tle_batch_set,
                    can_retry=retry_cap < args.max_timelimit,
                )

                # Merge retry results into existing timing data
                retry_td = collect_timing_data(sol, retry_results, retry_cap)
                td = merge_timing_data(timing_data[sol.name], retry_td)
                timing_data[sol.name] = td

                # Save cache after each retry run
                cached_data[sol.name] = td
                save_cache(cache_path, cached_data, current_start)

        # Update baselines with final timing data for this solution.
        # Each solution contributes its max non-TLE batch time.
        td = timing_data[sol.name]
        non_tle_times = [t for t in td.batch_max_times.values() if t is not None]
        if non_tle_times:
            baseline_max_times[lang].append(max(non_tle_times))

    # === Phase 2: Compute initial timelimits ===
    infob("\n===== Computing Timelimits =====")

    # Group by language
    langs_present = sorted(
        set(e.lang for e in expectations if e.lang != Langs.Lang.unknown),
        key=lambda lang: lang.name,
    )

    tl_results: dict[Langs.Lang, TimelimitResult] = {}
    for lang in langs_present:
        result = compute_timelimit_for_language(
            lang, timing_data, expectations, batches
        )
        tl_results[lang] = result

    # === Phase 3: Robustness verification ===
    # Check must-TLE batches that TLE'd at caps close to the recommended TL.
    # Rerun at higher caps to find actual times. Recompute. Iterate until
    # stable or valid range gap is wide enough.
    sol_by_name: dict[str, Solution] = {sol.name: sol for sol in solutions}
    MAX_VERIFICATION_ROUNDS = 3
    GAP_THRESHOLD = 10.0  # Stop if valid range gap >= 10x

    for verification_round in range(MAX_VERIFICATION_ROUNDS):
        # Check if any language needs verification
        any_needs_verification = False
        for lang in langs_present:
            result = tl_results[lang]
            if result.recommended is None:
                continue

            # Skip if valid range gap is already wide enough
            gap = valid_range_gap(result)
            if gap >= GAP_THRESHOLD:
                continue

            to_verify = find_must_tle_needing_verification(
                timing_data, expectations, batches, result.recommended
            )
            # Filter to this language's solutions
            lang_to_verify = [
                (exp, vbatches) for exp, vbatches in to_verify if exp.lang == lang
            ]
            if not lang_to_verify:
                continue

            any_needs_verification = True
            infob(
                f"\n===== Robustness Verification (round {verification_round + 1}) "
                f"for {lang.name} ====="
            )

            for exp, uncertain_batches in lang_to_verify:
                sol = sol_by_name.get(exp.solution.name)
                if sol is None:
                    continue
                name = Path(sol.name).name
                td = timing_data[sol.name]
                prev_cap = td.timelimit_used

                # Rerun at a higher cap to discover actual times
                verify_cap = compute_retry_cap(prev_cap, args.max_timelimit)
                if verify_cap <= prev_cap:
                    infob(
                        f"  {name}: already at max cap ({prev_cap:.2f}s), "
                        f"cannot verify batches: {', '.join(uncertain_batches)}"
                    )
                    continue

                infob(
                    f"  Verifying {name} (cap={verify_cap:.2f}s, "
                    f"was={prev_cap:.2f}s, "
                    f"uncertain batches: {', '.join(uncertain_batches)})"
                )

                verify_batch_set = set(uncertain_batches)
                verify_results = run_solution_on_inputs(
                    sol,
                    inputs,
                    args.indir,
                    args.outdir,
                    args.outext,
                    args.tempext,
                    checker,
                    timedelta(seconds=verify_cap),
                    Config.threads,
                    only_batches=verify_batch_set,
                    # No early abort: we want to discover actual times
                    can_retry=False,
                )

                verify_td = collect_timing_data(sol, verify_results, verify_cap)
                td = merge_timing_data(timing_data[sol.name], verify_td)
                timing_data[sol.name] = td

                # Report discoveries
                for batch in uncertain_batches:
                    t = td.batch_max_times.get(batch)
                    if t is not None:
                        infob(
                            f"    {name} batch {batch}: actual time "
                            f"{t:.3f}s (was TLE at {prev_cap:.2f}s)"
                        )
                    else:
                        infob(
                            f"    {name} batch {batch}: still TLE at {verify_cap:.2f}s"
                        )

                # Save cache after each verification run
                cached_data[sol.name] = td
                save_cache(cache_path, cached_data, current_start)

        if not any_needs_verification:
            break

        # Recompute timelimits with updated data
        infob("\n  Recomputing timelimits after verification...")
        for lang in langs_present:
            result = compute_timelimit_for_language(
                lang, timing_data, expectations, batches
            )
            tl_results[lang] = result

    # === Output ===
    print_timing_table(timing_data, expectations, batches, tl_results)
    print_results(tl_results, batches)
    print_warnings(timing_data, expectations, batches, tl_results)

    info("")
    check_data_folder_size(args.outdir)
    info(str(default_logger.statistics))

    # Clean temp files
    if args.cleartemp:
        for inp in inputs:
            prefix = str(args.outdir / inp.with_suffix(""))
            tfile = Path(prefix + ".fl." + args.tempext)
            if tfile.exists():
                tfile.unlink()

    if args.clearbin:
        cleanup(solutions)
