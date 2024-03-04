# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import subprocess
from collections import defaultdict
from threading import Event
from typing import Optional, Union

from input_tool.common.commands import to_base_alnum
from input_tool.common.messages import Logger, default_logger, fit_text_into_screen
from input_tool.common.programs.program import Program


class Checker(Program):
    def __init__(self, name: str, show_output: bool = False):
        super().__init__(name)
        self.output_ready: defaultdict[str, Event] = defaultdict(Event)
        self.show_output = show_output
        if name == "diff":
            self.run_cmd = "diff " + (
                "-y -W 80 --strip-trailing-cr" if show_output else "-q"
            )
            self.compilecmd = None
            self.forceexecute = True

    @staticmethod
    def filename_befits(filename: str) -> bool:
        return Checker.which_checker_format(filename) is not None

    @staticmethod
    def which_checker_format(filename: str) -> Union[str, None]:
        filename = to_base_alnum(filename)
        prefixes = ["diff", "check", "chito", "tester"]
        for prefix in prefixes:
            if filename.startswith(prefix):
                return prefix
        return None

    def compare_mask(self) -> tuple[int, int, str]:
        return (3, 0, self.name)

    def diff_cmd(self, ifile: str, ofile: str, tfile: str) -> Union[str, None]:
        diff_map = {
            "diff": " %s %s" % (ofile, tfile),
            "check": " %s %s %s > /dev/null" % (ifile, ofile, tfile),
            "chito": " %s %s %s > /dev/null" % (ifile, tfile, ofile),
            "test": " %s %s %s %s %s" % ("./", "./", ifile, ofile, tfile),
            "tester": " %s %s %s %s %s" % ("./", "./", ifile, ofile, tfile),
        }
        prefix = self.which_checker_format(self.name)
        if prefix:
            return self.run_cmd + diff_map[prefix]
        return None

    def check(
        self, ifile: str, ofile: str, tfile: str, logger: Optional[Logger] = None
    ) -> int:
        logger = default_logger if logger is None else logger
        cmd = self.diff_cmd(ifile, ofile, tfile)
        if cmd is None:
            logger.fatal(f"Unsupported checker {self.name}")
            return -1
        result = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if not self.quiet:
            logger.plain(result.stderr.decode("utf-8"))
        if result.returncode not in (0, 1):
            logger.warning(f"Checker exited with status {result}")
        if self.show_output and result.returncode:
            logger.infod(fit_text_into_screen(result.stdout.decode("utf-8"), 5, 80))
        return result.returncode
