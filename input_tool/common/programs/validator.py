from typing import Optional, Tuple

from input_tool.common.commands import to_base_alnum
from input_tool.common.messages import Color, default_logger, Logger, Status
from input_tool.common.programs.checker import Checker
from input_tool.common.programs.solution import Solution

class Validator(Solution):
    def __init__(self, name: str):
        super().__init__(name)
        self.statistics.result = Status.valid

    @staticmethod
    def filename_befits(filename: str) -> bool:
        return to_base_alnum(filename).startswith("val")

    def compare_mask(self) -> Tuple[int, int, str]:
        return (-2, 0, self.name)

    def updated_status(self, original: Status, new: Status) -> Status:
        if original == Status.err or new == Status.err:
            return Status.err
        if original == Status.valid:
            return new
        return original
    
    def get_statistics_color_and_points(self) -> Tuple[Color, str]:
        color = Color.score_color(self.statistics.result == Status.valid, 1)
        return color, ""

    def run_args(self, ifile: str) -> str:
        return " ".join(ifile.split("/")[-1].split(".")) + " "

    def run(
        self,
        ifile: str,
        ofile: str,
        tfile: str,
        checker: Checker,
        is_output_generator: bool = False,
        logger: Optional[Logger] = None,
    ) -> None:
        logger = default_logger if logger is None else logger
        run_times, status = self._run(
            ifile, ofile, tfile, None, is_output_generator, logger
        )

        if status is not Status.ok:
            self.statistics.failedbatches.add(self.parse_batch(ifile))
        if status in (Status.ok, Status.wa):
            status = Status.valid

        self.record(ifile, status, run_times)
        self.output_testcase_summary(ifile, status, run_times, logger)