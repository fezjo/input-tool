# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import os
import subprocess

from input_tool.common.commands import Config
from input_tool.common.messages import Status, warning
from input_tool.common.programs.program import Program
from input_tool.common.types import Path


class Generator(Program):
    def compare_mask(self) -> tuple[int, int, str]:
        return (4, 0, self.name)

    def generate(self, ifile: Path, text: str) -> Status:
        osc = Config.os_config
        ulimit_cmd = (
            f"{osc.cmd_ulimit} -m {osc.mem_unlimited}; "
            f"{osc.cmd_ulimit} -s {osc.mem_unlimited}"
        )
        cmd = f"{ulimit_cmd}; {self.run_cmd} > {ifile}"
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
        p.communicate(str.encode(text))
        if not p.returncode and not os.path.exists(ifile):
            warning(
                "Generator ran successfully, but output file was not created. What?"
            )
        return Status.exc if p.returncode else Status.ok
