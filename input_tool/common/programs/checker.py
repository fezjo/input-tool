from collections import defaultdict
import subprocess
from threading import Event
from typing import DefaultDict, Optional, Tuple

from input_tool.common.commands import to_base_alnum
from input_tool.common.messages import default_logger, Logger
from input_tool.common.programs.program import Program


class Checker(Program):
    def __init__(self, name: str):
        super().__init__(name)
        self.output_ready: DefaultDict[str, Event] = defaultdict(Event)
        if name == "diff":
            self.run_cmd = "diff"
            self.compilecmd = None
            self.forceexecute = True

    @staticmethod
    def filename_befits(filename: str) -> str | None:
        filename = to_base_alnum(filename)
        prefixes = ["diff", "check", "chito", "test"]
        for prefix in prefixes:
            if filename.startswith(prefix):
                return prefix
        return None

    def compare_mask(self) -> Tuple[int, int, str]:
        return (-3, 0, self.name)

    def diff_cmd(self, ifile: str, ofile: str, tfile: str) -> str | None:
        diff_map = {
            "diff": " %s %s > /dev/null" % (ofile, tfile),
            "check": " %s %s %s > /dev/null" % (ifile, ofile, tfile),
            "chito": " %s %s %s > /dev/null" % (ifile, tfile, ofile),
            "test": " %s %s %s %s %s" % ("./", "./", ifile, ofile, tfile),
        }
        prefix = self.filename_befits(self.name)
        if prefix:
            return self.run_cmd + diff_map[prefix]
        return None

    def check(
        self, ifile: str, ofile: str, tfile: str, logger: Optional[Logger] = None
    ) -> int:
        logger = default_logger if logger is None else logger
        cmd = self.diff_cmd(ifile, ofile, tfile)
        if cmd is None:
            logger.error(f"Unsupported checker {self.name}")
            return -1
        result = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE)
        if not self.quiet:
            logger.plain(result.stderr.decode("utf-8"))
        if not result.returncode in (0, 1):
            logger.warning(f"Checker exited with status {result}")
        return result.returncode
