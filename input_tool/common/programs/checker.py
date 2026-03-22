# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import subprocess
from collections import defaultdict
from enum import Enum
from threading import Event
from typing import Optional

from input_tool.common.commands import to_base_alnum
from input_tool.common.messages import Logger, default_logger, fit_text_into_screen
from input_tool.common.programs.program import Program
from input_tool.common.types import Path, ShellCommand, TempFile


class CheckerType(Enum):
    # just a simple byte comparator
    diff = "diff"
    # custom checker
    check = "check"
    chito = "chito"
    test = "test"
    tester = "tester"
    # legacy usage, `./sol < fifo | ./check > fifo`
    interactive_pipe = "interactive_pipe"
    # used by KSP Judge, with additional info in task.json
    interactive_kspjudge = "interactive_kspjudge"

    def is_interactive(self) -> bool:
        return self in (CheckerType.interactive_pipe, CheckerType.interactive_kspjudge)


class Checker(Program):
    def __init__(self, name: str, show_output: bool = False):
        super().__init__(name)
        self.output_ready: defaultdict[Path, Event] = defaultdict(Event)
        self.show_output = show_output
        checker_type = self.determine_checker_type(name)
        if checker_type is None:
            assert False, f"Unsupported checker {self.name}"
        self.type = checker_type
        if name == "diff":
            self.run_cmd = ShellCommand(
                "diff " + ("-y -W 120 --strip-trailing-cr" if show_output else "-q")
            )
            self.compilecmd = None
            self.force_execute = True

    @staticmethod
    def filename_befits(filename: str) -> bool:
        return Checker.determine_checker_type(filename) is not None

    @staticmethod
    def determine_checker_type(filename: str) -> Optional[CheckerType]:
        basename = to_base_alnum(filename)
        prefixes: tuple[tuple[str, CheckerType], ...] = (
            ("diff", CheckerType.diff),
            ("check", CheckerType.check),
            ("chito", CheckerType.chito),
            ("tester", CheckerType.tester),
            ("test", CheckerType.test),
        )
        for prefix, checker_type in prefixes:
            if basename.startswith(prefix):
                return checker_type
        if basename.startswith("interactiver") or basename.startswith("interaktiver"):
            if Path("task.json").is_file():
                return CheckerType.interactive_kspjudge
            else:
                return CheckerType.interactive_pipe
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
            CheckerType.diff: f" {ofile} {tfile}",
            CheckerType.check: f" {ifile} {ofile} {tfile}",
            CheckerType.chito: f" {ifile} {tfile} {ofile}",
            CheckerType.test: f" ./ ./ {ifile} {ofile} {tfile}",
            CheckerType.tester: f" ./ ./ {ifile} {ofile} {tfile}",
        }
        if self.run_cmd is not None and self.type in diff_map:
            return self.run_cmd + diff_map[self.type]
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
