# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import subprocess
from collections import defaultdict
from threading import Event
from typing import Optional

from input_tool.common.commands import to_base_alnum
from input_tool.common.messages import Logger, default_logger, fit_text_into_screen
from input_tool.common.programs.program import Program
from input_tool.common.types import Path, ShellCommand, TempFile


class Checker(Program):
    def __init__(self, name: str, show_output: bool = False):
        super().__init__(name)
        self.output_ready: defaultdict[Path, Event] = defaultdict(Event)
        self.show_output = show_output
        if name == "diff":
            self.run_cmd = ShellCommand(
                "diff " + ("-y -W 80 --strip-trailing-cr" if show_output else "-q")
            )
            self.compilecmd = None
            self.force_execute = True

    @staticmethod
    def filename_befits(filename: str) -> bool:
        return Checker.which_checker_format(filename) is not None

    @staticmethod
    def which_checker_format(filename: str) -> Optional[str]:
        basename = to_base_alnum(filename)
        prefixes = ["diff", "check", "chito", "tester"]
        for prefix in prefixes:
            if basename.startswith(prefix):
                return prefix
        return None

    def compare_mask(self) -> tuple[int, int, str]:
        return (3, 0, self.name)

    def diff_cmd(
        self,
        ifile: Path,
        ofile: Path,
        tfile: TempFile,
    ) -> Optional[str]:
        diff_map = {
            "diff": f" {ofile} {tfile}",
            "check": f" {ifile} {ofile} {tfile}",
            "chito": f" {ifile} {tfile} {ofile}",
            "test": f" ./ ./ {ifile} {ofile} {tfile}",
            "tester": f" ./ ./ {ifile} {ofile} {tfile}",
        }
        prefix = self.which_checker_format(self.name)
        if prefix and self.run_cmd is not None:
            return self.run_cmd + diff_map[prefix]
        return None

    def check(
        self,
        ifile: Path,
        ofile: Path,
        tfile: TempFile,
        logger: Optional[Logger] = None,
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
