# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import os
import shlex
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable, Optional, Union

from input_tool.common.commands import Config, Langs, natural_sort_key, to_base_alnum
from input_tool.common.messages import Color, Logger, Status, default_logger, table_row
from input_tool.common.programs.checker import Checker, CheckerType
from input_tool.common.programs.program import Program
from input_tool.common.task_history import TASK_HISTORY, TaskHistory
from input_tool.common.types import Path, ShellCommand, TempFile


def create_temp_file() -> TempFile:
    with tempfile.NamedTemporaryFile(delete=False) as file:
        return TempFile(file.name)


def create_temp_fifo() -> TempFile:
    fifo = create_temp_file()
    os.unlink(fifo)
    return fifo


def parse_interactive_verdict(
    result_file: TempFile,
    logger: Logger,
) -> Optional[Status]:
    if not result_file.exists():
        return None
    try:
        with open(result_file, "r") as f_result:
            lines = [x.strip() for x in f_result.read().splitlines() if x.strip()]
    except OSError as e:
        logger.warning(repr(e))
        return None

    if not lines:
        return None

    verdict = lines[0].upper().rstrip("?")
    mapping = {
        "OK": Status.ok,
        "AC": Status.ok,
        "WA": Status.wa,
        "PRV": Status.wa,
        "TLE": Status.tle,
        "TO": Status.tle,
        "EXC": Status.exc,
        "RE": Status.exc,
        "ERR": Status.err,
    }
    if verdict in mapping:
        return mapping[verdict]
    logger.warning(f"Unrecognized interactive verdict '{verdict}'")
    return Status.err


class Solution(Program):
    @dataclass
    class Statistics:
        maxtime: timedelta
        sumtime: timedelta
        batchresults: dict[str, Status]
        result: Status
        times: defaultdict[str, list[Optional[tuple[timedelta, ...]]]]
        failedbatches: set[str]

    def __init__(self, name: str):
        super().__init__(name)
        self.statistics = Solution.Statistics(
            maxtime=timedelta(milliseconds=-1),
            sumtime=timedelta(),
            batchresults={},
            result=Status.ok,
            times=defaultdict(list),
            failedbatches=set(),
        )

    @staticmethod
    def filename_befits(filename: str) -> bool:
        return to_base_alnum(filename).startswith("sol")

    def updated_status(self, original: Status, new: Status) -> Status:
        if original == Status.err or new == Status.err:
            return Status.err
        if original == Status.ok:
            return new
        return original

    def compare_mask(self) -> tuple[int, int, str]:
        filename = Path(self.name).name
        name = Path(filename).stem
        parts = name.split("-")
        score = 0
        if "vzorak" in parts or "vzor" in parts:
            score += 2000
        if name == "sol":
            score += 1000
        if name.startswith("sol") and len(parts) > 1:
            if parts[1].isnumeric():
                score += int(parts[1])
            elif parts[1] == "wa":
                score -= 100

        language = Langs.from_filename(filename)
        lang_rank = Langs.expected_performance_ranking.index(language)
        # TODO: this is a bit hacky
        ranked_name = "{}_{}".format(chr(ord("9") - lang_rank), self.name)

        return (1, score, ranked_name)

    def compute_time_statistics(self) -> None:
        self.statistics.sumtime = timedelta()
        for batch, result in self.statistics.batchresults.items():
            if result != Status.ok:
                continue
            times = [ts[0] for ts in self.statistics.times[batch] if ts]
            self.statistics.maxtime = max(self.statistics.maxtime, max(times))
            self.statistics.sumtime += sum(times, timedelta())

    def grade_results(self) -> tuple[int, int]:
        points, maxpoints = 0, 0
        for batch, result in self.statistics.batchresults.items():
            if "sample" in batch:
                continue
            maxpoints += 1
            points += result == Status.ok
        return points, maxpoints

    def get_statistics_color_and_points(self) -> tuple[Color, str]:
        points, maxpoints = self.grade_results()
        color = Color.score_color(points, maxpoints)
        return color, str(points)

    def get_statistics(self) -> str:
        def to_miliseconds(t: timedelta) -> int:
            return round(t.total_seconds() * 1000)

        self.compute_time_statistics()
        color, points = self.get_statistics_color_and_points()
        batchresults = sorted(
            self.statistics.batchresults.items(), key=lambda x: natural_sort_key(x[0])
        )
        batch_letters: list[str] = []
        for batch, status in batchresults:
            letter = str(status.set_warntle(False))[0]
            if "sample" in batch:
                letter = letter.lower()
            batch_letters.append(Color.colorize(letter, Color.status[status]))
        batch_col_len = max(7, len(batchresults))
        widths = (Config.cmd_maxlen, 8, 9, 6, 6, batch_col_len)
        values: list[Union[str, int, Status]] = [
            self.name,
            to_miliseconds(self.statistics.maxtime),
            to_miliseconds(self.statistics.sumtime),
            points,
            self.statistics.result,
            "".join(batch_letters),
        ]
        return table_row(color, values, widths, "<>>>><")

    def get_json(self) -> dict[str, Any]:
        self.compute_time_statistics()
        _color, points = self.get_statistics_color_and_points()
        return {
            "name": self.name,
            "maxtime": self.statistics.maxtime,
            "sumtime": self.statistics.sumtime,
            "points": points,
            "result": self.statistics.result,
            "batchresults": self.statistics.batchresults,
            "times": self.statistics.times,
            "failedbatches": self.statistics.failedbatches,
        }

    @staticmethod
    def parse_batch(ifile: Path) -> str:
        inp = ifile.stem
        return inp if inp.endswith("sample") else inp.rsplit(".", 1)[0]

    def record(
        self,
        ifile: Path,
        status: Status,
        times: Optional[Iterable[timedelta]],
    ) -> None:
        batch = self.parse_batch(ifile)
        batchresults = self.statistics.batchresults
        batchresults[batch] = self.updated_status(
            batchresults.get(batch, Status.ok), status
        )
        self.statistics.times[batch].append(None if times is None else tuple(times))

        old_status = self.statistics.result
        new_status = self.updated_status(old_status, status)
        if old_status == new_status == status and status.warntle is not None:
            new_status = new_status.set_warntle(
                status.warntle if status.warntle else old_status.warntle
            )
        self.statistics.result = new_status

    def get_timelimit(self, timelimits: Config.Timelimit) -> timedelta:
        return Config.get_timelimit(timelimits, self.extension, self.lang)

    @staticmethod
    def get_wrapper_cmds(timelimit: timedelta = timedelta(0), memorylimit: float = 0.0):
        f_timefile = tempfile.NamedTemporaryFile(delete=False)
        f_timefile.close()
        timefile = TempFile(f_timefile.name)

        osc = Config.os_config
        memorylimit_kb = int(memorylimit * 1024) if memorylimit else osc.mem_unlimited
        # -d = Data segment (heap), -m = Resident memory (RSS), -s = Stack size, -v = Virtual memory
        ulimit_cmds = (
            # f"{osc.cmd_ulimit} -s {osc.mem_unlimited}", # NOTE: if you remove the below limits, uncomment this
            f"{osc.cmd_ulimit} -d {memorylimit_kb}",
            f"{osc.cmd_ulimit} -m {memorylimit_kb}",
            f"{osc.cmd_ulimit} -s {memorylimit_kb}",
            f"{osc.cmd_ulimit} -v {memorylimit_kb}",
        )
        time_prefix = (
            f'{osc.cmd_time} -f "%e %U %S" -a -o {timefile} -q'
            if Config.rus_time
            else ""
        )
        date_cmd = f"{osc.cmd_date} +%s%N >> {timefile}"

        timeout_prefix = (
            f"{osc.cmd_timeout} {timelimit.total_seconds()}" if timelimit else ""
        )

        return timefile, ulimit_cmds, timeout_prefix, time_prefix, date_cmd

    def get_exec_cmd(
        self,
        ifile: Path,
        tfile: TempFile,
        timelimit: timedelta = timedelta(0),
        memorylimit: float = 0.0,
    ) -> tuple[TempFile, ShellCommand]:
        timefile, ulimit_cmds, timeout_prefix, time_prefix, date_cmd = (
            self.get_wrapper_cmds(timelimit, memorylimit)
        )
        prog_cmd = f"{self.run_cmd} {self.run_args(ifile)} < {ifile} > {tfile}"
        cmds = (
            *ulimit_cmds,
            date_cmd,
            f"{time_prefix} {timeout_prefix} {prog_cmd}",
            "rc=$?",
            date_cmd,
            "exit $rc",
        )
        cmd = ShellCommand("; ".join(cmds))
        return timefile, cmd

    def get_interactive_wrapped_cmd(
        self,
        body_cmd: str,
        fifo_paths: Iterable[TempFile],
        timelimit: timedelta,
        memorylimit: float,
    ) -> tuple[TempFile, ShellCommand]:
        timefile, ulimit_cmds, timeout_prefix, time_prefix, date_cmd = (
            self.get_wrapper_cmds(timelimit, memorylimit)
        )
        fifo_clean = "rm -f " + " ".join(map(str, fifo_paths))
        fifo_create = "; ".join(f"mkfifo {path}" for path in fifo_paths)

        cmds = (
            *ulimit_cmds,
            date_cmd,
            f"trap '{fifo_clean}' EXIT; {fifo_create}",
            f"{time_prefix} {timeout_prefix} sh -c {shlex.quote(body_cmd)}",
            "rc=$?",
            date_cmd,
            "exit $rc",
        )
        cmd = ShellCommand("; ".join(cmds))
        return timefile, cmd

    def get_interactive_exec_cmd(
        self,
        ifile: Path,
        checker: Checker,
        timelimit: timedelta = timedelta(0),
        memorylimit: float = 0.0,
    ) -> tuple[TempFile, ShellCommand]:
        assert checker.type == CheckerType.interactive_pipe

        fifo = create_temp_fifo()
        run_cmd = f"{self.run_cmd} {self.run_args(ifile)}".strip()
        pipeline = f"{run_cmd} < {fifo} | {checker.run_cmd} {ifile} > {fifo}"
        timefile, cmd = self.get_interactive_wrapped_cmd(
            pipeline,
            (fifo,),
            timelimit,
            memorylimit,
        )
        return timefile, cmd

    def get_interactive_kspjudge_exec_cmd(
        self,
        ifile: Path,
        checker: Checker,
        timelimit: timedelta = timedelta(0),
        memorylimit: float = 0.0,
    ) -> tuple[TempFile, TempFile, ShellCommand]:
        assert checker.type == CheckerType.interactive_kspjudge

        fifo_in = create_temp_fifo()
        fifo_out = create_temp_fifo()
        result_file = create_temp_file()

        batch = ifile.name.split(".", 1)[0]
        run_cmd = f"{self.run_cmd} {self.run_args(ifile)}".strip()
        body_cmd = (
            f"{checker.run_cmd} {batch} {ifile.stem}"
            f" {fifo_in} {fifo_out} {result_file} &"
            " checker_pid=$!;"
            f" {run_cmd} < {fifo_in} > {fifo_out};"
            " sol_rc=$?;"
            " wait $checker_pid;"
            " checker_rc=$?;"
            " if [ $sol_rc -ne 0 ]; then exit $sol_rc; fi;"
            " exit $checker_rc"
        )
        timefile, cmd = self.get_interactive_wrapped_cmd(
            body_cmd,
            (fifo_in, fifo_out),
            timelimit,
            memorylimit,
        )
        return timefile, result_file, cmd

    def run_args(self, ifile: Path) -> str:
        return ""

    def translate_exit_code_to_status(self, exit_code: int) -> Status:
        if exit_code == 0:
            return Status.ok
        if exit_code == 124:
            return Status.tle
        if exit_code > 0:
            return Status.exc
        return Status.err

    def get_times(
        self, timefile: TempFile, logger: Logger = default_logger
    ) -> Optional[list[timedelta]]:
        try:
            with open(timefile, "r") as tf:
                ptime_start, *rus_times, ptime_end = map(float, tf.read().split())
                run_times = [timedelta(seconds=(ptime_end - ptime_start) / 1e9)] + [
                    timedelta(seconds=t) for t in rus_times
                ]
                return run_times
        except (OSError, ValueError) as e:
            logger.warning(repr(e))
        return None

    def _run(
        self,
        ifile: Path,
        ofile: Path,
        tfile: TempFile,
        checker: Optional[Checker],
        is_output_generator: bool,
        logger: Logger,
        callbacks: TaskHistory.callbacks_t,
    ) -> tuple[Optional[list[timedelta]], Status]:
        if not self.ready:
            logger.fatal(f"{self.name} not prepared for execution")
        cb_set_process, cb_was_killed, cb_kill_siblings = callbacks

        run_times: Optional[list[timedelta]] = None
        timelimit = self.get_timelimit(Config.timelimits)
        memorylimit = float(Config.memorylimit)
        result_file: Optional[TempFile] = None
        checker_type = checker.type if checker else None
        if checker_type == CheckerType.interactive_kspjudge:
            timefile, result_file, cmd = self.get_interactive_kspjudge_exec_cmd(
                ifile, checker, timelimit, memorylimit
            )
        elif checker_type == CheckerType.interactive_pipe:
            timefile, cmd = self.get_interactive_exec_cmd(
                ifile, checker, timelimit, memorylimit
            )
        else:
            timefile, cmd = self.get_exec_cmd(ifile, tfile, timelimit, memorylimit)
        try:
            if cb_was_killed():
                return None, Status.tle
            with subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,  # stdout goes to file anyway
                stderr=subprocess.PIPE,
            ) as process:
                cb_set_process(process)
                process.wait()
                if cb_was_killed():
                    return None, Status.tle
                TASK_HISTORY.end(self.name, self.parse_batch(ifile), str(ifile))
                if not self.quiet and process.stderr:
                    logger.infod(process.stderr.read().decode("utf-8"))
                status = self.translate_exit_code_to_status(process.returncode)
                if (
                    checker_type == CheckerType.interactive_pipe
                    and status == Status.exc
                ):
                    # with this kind of interactiver, wa is signaled by nonzero exit code
                    status = Status.wa
                if (
                    checker_type == CheckerType.interactive_kspjudge
                    and status == Status.ok
                ):
                    # with this kind of interactiver, there is extra information written in the result file
                    assert result_file is not None
                    verdict_status = parse_interactive_verdict(result_file, logger)
                    if verdict_status is not None:
                        status = verdict_status
                    elif status == Status.ok:
                        status = Status.err
            if status == Status.tle:
                cb_kill_siblings()

            run_times = self.get_times(timefile, logger)
            if not run_times and status == Status.ok:
                status = Status.exc
            if (
                checker is not None
                and not checker.type.is_interactive()
                and status == Status.ok
            ):
                if not is_output_generator:
                    checker.output_ready[ifile].wait()
                if checker.check(ifile, ofile, tfile, logger):
                    status = Status.wa
        except Exception as e:
            status = Status.err
            logger.warning(repr(e))
        finally:
            if timefile.exists():
                timefile.unlink()
            if result_file is not None and result_file.exists():
                result_file.unlink()

        return run_times, status

    def output_testcase_summary(
        self,
        ifile: Path,
        status: Status,
        run_times: Optional[Iterable[timedelta]],
        logger: Logger,
    ) -> None:
        run_cmd = ("{:<" + str(Config.cmd_maxlen) + "s}").format(self.name)
        time_format = ["{:6d}ms", "{:6d}ms [{:6.2f}={:6.2f}+{:6.2f}]"][Config.rus_time]
        if run_times is None:
            time = " NO DATA".ljust(len(time_format.format(0, 0, 0, 0)))
        else:
            seconds = [round(t.total_seconds(), 3) for t in run_times]
            time = time_format.format(int(seconds[0] * 1000), *seconds[1:])

        if Config.inside_oneline:
            input = ("{:" + str(Config.inside_inputmaxlen) + "s}").format(ifile.name)
            summary = "{} < {} {}".format(run_cmd, input, time)
        else:
            summary = "    {}  {}".format(run_cmd, time)

        logger.plain(
            "{} {}\n".format(Color.status_colorize(status, summary), status.colored())
        )

        if status == Status.err:
            logger.fatal("Internal error. Testing will not continue")

    def run(
        self,
        ifile: Path,
        ofile: Path,
        tfile: TempFile,
        checker: Checker,
        is_output_generator: bool = False,
        logger: Optional[Logger] = None,
    ) -> Optional[Status]:
        batch = self.parse_batch(ifile)
        task = str(ifile)
        TASK_HISTORY.start(self.name, batch, task)
        if Config.fail_skip and batch in self.statistics.failedbatches:
            TASK_HISTORY.end(self.name, batch, task, True)
            return None

        callbacks = TASK_HISTORY.get_callbacks(self.name, batch, task)
        logger = default_logger if logger is None else logger
        run_times, status = self._run(
            ifile, ofile, tfile, checker, is_output_generator, logger, callbacks
        )

        if status is not Status.ok:
            self.statistics.failedbatches.add(batch)

        warntle = self.get_timelimit(Config.warn_timelimits)
        status = status.set_warntle(
            warntle != timedelta(0)
            and run_times is not None
            and run_times[0] >= warntle
        )

        self.record(ifile, status, run_times)
        self.output_testcase_summary(ifile, status, run_times, logger)
        return status
