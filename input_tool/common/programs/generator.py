import subprocess

from input_tool.common.messages import Status
from input_tool.common.programs.program import Program


class Generator(Program):
    def compare_mask(self) -> tuple[int, int, str]:
        return (-4, 0, self.name)

    def generate(self, ifile: str, text: str) -> Status:
        cmd = f"{self.run_cmd} > {ifile}"
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
        p.communicate(str.encode(text))
        return Status.exc if p.returncode else Status.ok
