from typing import Tuple

from input_tool.common.commands import Config, to_base_alnum
from input_tool.common.messages import Color, Status, table_row
from input_tool.common.programs.solution import Solution

class Validator(Solution):
    def __init__(self, name: str):
        super().__init__(name)
        self.is_validator = True
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

    def grade_results(self) -> None:
        for batch, _ in self.statistics.batchresults.items():
            times = [ts[0] for ts in self.statistics.times[batch] if ts]
            self.statistics.maxtime = max(self.statistics.maxtime, max(times))
            self.statistics.sumtime += sum(times)

    def get_statistics(self) -> str:
        self.grade_results()
        color = Color.score_color(self.statistics.result == Status.valid, 1)
        widths = (Config.cmd_maxlen, 8, 9, 6, 6)
        colnames = [
            self.run_cmd,
            self.statistics.maxtime,
            self.statistics.sumtime,
            "",
            self.statistics.result,
        ]

        return table_row(color, colnames, widths, [-1, 1, 1, 1, 0])

    def run_args(self, ifile: str) -> str:
        return " ".join(ifile.split("/")[-1].split(".")) + " "
