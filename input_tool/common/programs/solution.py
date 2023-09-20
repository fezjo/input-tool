from collections import defaultdict
from dataclasses import dataclass
import os
import subprocess
import tempfile
from typing import Optional, Sequence, Tuple

from input_tool.common.commands import Config, Langs, to_base_alnum
from input_tool.common.messages import Color, default_logger, Logger, Status, table_row
from input_tool.common.programs.checker import Checker
from input_tool.common.programs.program import Program


class Solution(Program):
    @dataclass
    class Statistics:
        maxtime: float
        sumtime: float
        batchresults: dict[str, Status]
        result: Status
        times: defaultdict[str, list[Optional[tuple[float, ...]]]]
        failedbatches: set[str]

    def __init__(self, name: str):
        super().__init__(name)
        self.statistics = Solution.Statistics(
            maxtime=-1,
            sumtime=0,
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

    def compare_mask(self) -> Tuple[int, int, str]:
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
        return (-1, -score, self.name)
    
    def compute_time_statistics(self) -> None:
        for batch, _ in self.statistics.batchresults.items():
            times = [ts[0] for ts in self.statistics.times[batch] if ts]
            self.statistics.maxtime = max(self.statistics.maxtime, max(times))
            self.statistics.sumtime += sum(times)

    def grade_results(self) -> tuple[int, int]:
        points, maxpoints = 0, 0
        for batch, result in self.statistics.batchresults.items():
            if "sample" in batch:
                continue
            maxpoints += 1
            if result != Status.ok:
                continue
            points += 1
        return points, maxpoints
    
    def get_statistics_color_and_points(self) -> Tuple[Color, str]:
        points, maxpoints = self.grade_results()
        color = Color.score_color(points, maxpoints)
        return color, str(points)

    def get_statistics(self) -> str:
        self.compute_time_statistics()
        color, points = self.get_statistics_color_and_points()
        widths = (Config.cmd_maxlen, 8, 9, 6, 6)
        colnames = [
            self.name,
            self.statistics.maxtime,
            self.statistics.sumtime,
            points,
            self.statistics.result,
        ]
        return table_row(color, colnames, widths, [-1, 1, 1, 1, 0])

    @staticmethod
    def parse_batch(ifile: str):
        name = os.path.basename(ifile)
        input, _ext = os.path.splitext(name)
        return input if input.endswith("sample") else input.rsplit(".", 1)[0]

    def record(
        self, ifile: str, status: Status, times: Optional[Sequence[float]]
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

    def get_timelimit(self, timelimits: dict[Langs.Lang | str, float]) -> float:
        if self.ext in timelimits:
            return timelimits[self.ext]
        if self.lang in timelimits:
            return timelimits[self.lang]
        return timelimits[Langs.Lang.unknown]

    def get_exec_cmd(
        self, ifile: str, tfile: str, timelimit: float = 0.0, memorylimit: float = 0.0
    ) -> Tuple[str, str]:
        timefile = tempfile.NamedTemporaryFile(delete=False)
        timefile.close()
        timefile = timefile.name

        str_memorylimit = int(memorylimit * 1024) if memorylimit else "unlimited"
        ulimit_cmd = "ulimit -m %s; ulimit -s %s" % (str_memorylimit, str_memorylimit)
        timelimit_cmd = "timeout %s" % timelimit if timelimit else ""
        time_cmd = ["", '/usr/bin/time -f "%s" -a -o %s -q' % ("%e %U %S", timefile)][
            Config.rus_time
        ]
        date_cmd = "date +%%s%%N >>%s" % timefile
        prog_cmd = "%s %s <%s >%s" % (self.run_cmd, self.run_args(ifile), ifile, tfile)
        cmd = "%s; %s; %s %s %s; rc=$?; %s; exit $rc" % (
            ulimit_cmd,
            date_cmd,
            time_cmd,
            timelimit_cmd,
            prog_cmd,
            date_cmd,
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

    def get_times(self, timefile: str):
        try:
            with open(timefile, "r") as tf:
                ptime_start, *run_times, ptime_end = map(float, tf.read().split())
                return [int((ptime_end - ptime_start) / 1e6)] + run_times
        except:
            return None

    def _run(
        self,
        ifile: str,
        ofile: str,
        tfile: str,
        checker: Optional[Checker],
        is_output_generator: bool,
        logger: Logger,
    ):
        if not self.ready:
            logger.error(f"{self.name} not prepared for execution")

        run_times: Optional[list[float]] = None
        timelimit = self.get_timelimit(Config.timelimits)
        memorylimit = float(Config.memorylimit)
        timefile, cmd = self.get_exec_cmd(ifile, tfile, timelimit, memorylimit)
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,  # stdout goes to file anyway
                stderr=subprocess.PIPE,
            )
            if not self.quiet:
                logger.colored(result.stderr.decode("utf-8"), Color.dim, "")
            status = self.translate_exit_code_to_status(result.returncode)

            run_times = self.get_times(timefile)
            if not run_times and status == Status.ok:
                status = Status.exc
            if checker is not None and status == Status.ok:
                if not is_output_generator:
                    checker.output_ready[ifile].wait()
                if checker.check(ifile, ofile, tfile, logger):
                    status = Status.wa
        except Exception as e:
            status = Status.err
            logger.warning(str(e))
        finally:
            if os.path.exists(timefile):
                os.remove(timefile)

        return run_times, status

    def output_testcase_summary(
        self,
        ifile: str,
        status: Status,
        run_times: Optional[Sequence[float]],
        logger: Logger,
    ) -> None:
        run_cmd = ("{:<" + str(Config.cmd_maxlen) + "s}").format(self.name)
        time_format = ["{:6d}ms", "{:6d}ms [{:6.2f}={:6.2f}+{:6.2f}]"][Config.rus_time]
        time = "err" if run_times is None else time_format.format(*run_times)

        if Config.inside_oneline:
            input = ("{:" + str(Config.inside_inputmaxlen) + "s}").format(
                (ifile.rsplit("/", 1)[1])
            )
            summary = "{} < {} {}".format(run_cmd, input, time)
        else:
            summary = "    {}  {}".format(run_cmd, time)

        logger.plain(
            "{} {}\n".format(Color.colorize(status, summary), status.colored())
        )

        if status == Status.err:
            logger.error("Internal error. Testing will not continue", doquit=True)

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
        if Config.fskip and batch in self.statistics.failedbatches:
            return

        logger = default_logger if logger is None else logger
        run_times, status = self._run(
            ifile, ofile, tfile, checker, is_output_generator, logger
        )

        if status is not Status.ok:
            self.statistics.failedbatches.add(batch)

        warntle = self.get_timelimit(Config.warn_timelimits) * 1000
        status = status.set_warntle(
            warntle != 0 and run_times is not None and run_times[0] >= warntle
        )

        self.record(ifile, status, run_times)
        self.output_testcase_summary(ifile, status, run_times, logger)
