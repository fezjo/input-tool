# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import os
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional, Sequence

from input_tool.common.commands import Config, Langs, to_base_alnum
from input_tool.common.messages import Color, Logger, Status, default_logger, table_row
from input_tool.common.programs.checker import Checker
from input_tool.common.programs.program import Program
from input_tool.common.task_history import TASK_HISTORY, TaskHistory


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
        filename = os.path.basename(self.name)
        name, _ext = os.path.splitext(filename)
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
        # NOTE: natural sort would be better
        batchresults = [v for k, v in sorted(self.statistics.batchresults.items())]
        batch_stats = "".join(
            Color.colorize(str(status.set_warntle(False))[0], Color.status[status])
            for status in batchresults
        )
        batch_col_len = max(7, len(batchresults))
        widths = (Config.cmd_maxlen, 8, 9, 6, 6, batch_col_len)
        colnames = [
            self.name,
            to_miliseconds(self.statistics.maxtime),
            to_miliseconds(self.statistics.sumtime),
            points,
            self.statistics.result,
            batch_stats,
        ]
        return table_row(color, colnames, widths, "<>>>><")

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
    def parse_batch(ifile: str) -> str:
        name = os.path.basename(ifile)
        inp, _ext = os.path.splitext(name)
        return inp if inp.endswith("sample") else inp.rsplit(".", 1)[0]

    def record(
        self, ifile: str, status: Status, times: Optional[Sequence[timedelta]]
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
        return Config.get_timelimit(timelimits, self.ext, self.lang)

    def get_exec_cmd(
        self,
        ifile: str,
        tfile: str,
        timelimit: timedelta = timedelta(0),
        memorylimit: float = 0.0,
    ) -> tuple[str, str]:
        f_timefile = tempfile.NamedTemporaryFile(delete=False)
        f_timefile.close()
        timefile = f_timefile.name

        osc = Config.os_config
        str_memorylimit = int(memorylimit * 1024) if memorylimit else osc.mem_unlimited
        ulimit_cmd = (
            f"{osc.cmd_ulimit} -m {str_memorylimit}; "
            f"{osc.cmd_ulimit} -s {str_memorylimit}"
        )
        timelimit_cmd = (
            f"{osc.cmd_timeout} {timelimit.total_seconds()}" if timelimit else ""
        )
        time_cmd = (
            f'{osc.cmd_time} -f "%e %U %S" -a -o {timefile} -q'
            if Config.rus_time
            else ""
        )
        date_cmd = f"{osc.cmd_date} +%s%N >> {timefile}"
        prog_cmd = f"{self.run_cmd} {self.run_args(ifile)} < {ifile} > {tfile}"
        cmd = (
            f"{ulimit_cmd}; {date_cmd}; "
            f"{time_cmd} {timelimit_cmd} {prog_cmd}; "
            f"rc=$?; {date_cmd}; exit $rc"
        )
        return timefile, cmd

    def run_args(self, ifile: str) -> str:
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
        self, timefile: str, logger: Logger = default_logger
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
        ifile: str,
        ofile: str,
        tfile: str,
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
                TASK_HISTORY.end(self.name, self.parse_batch(ifile), ifile)
                if not self.quiet and process.stderr:
                    logger.infod(process.stderr.read().decode("utf-8"))
                status = self.translate_exit_code_to_status(process.returncode)
            if status == Status.tle:
                cb_kill_siblings()

            run_times = self.get_times(timefile, logger)
            if not run_times and status == Status.ok:
                status = Status.exc
            if checker is not None and status == Status.ok:
                if not is_output_generator:
                    checker.output_ready[ifile].wait()
                if checker.check(ifile, ofile, tfile, logger):
                    status = Status.wa
        except Exception as e:
            status = Status.err
            logger.warning(repr(e))
        finally:
            if os.path.exists(timefile):
                os.remove(timefile)

        return run_times, status

    def output_testcase_summary(
        self,
        ifile: str,
        status: Status,
        run_times: Optional[Sequence[timedelta]],
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
            input = ("{:" + str(Config.inside_inputmaxlen) + "s}").format(
                (ifile.rsplit("/", 1)[1])
            )
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
        ifile: str,
        ofile: str,
        tfile: str,
        checker: Checker,
        is_output_generator: bool = False,
        logger: Optional[Logger] = None,
    ) -> None:
        batch = self.parse_batch(ifile)
        TASK_HISTORY.start(self.name, batch, ifile)
        if Config.fail_skip and batch in self.statistics.failedbatches:
            TASK_HISTORY.end(self.name, batch, ifile, True)
            return

        callbacks = TASK_HISTORY.get_callbacks(self.name, batch, ifile)
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
