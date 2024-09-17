# © 2023 fezjo
import os
import shutil
from dataclasses import dataclass
from typing import Iterable, Optional

from input_tool.common.messages import warning
from input_tool.common.types import ProgramName


@dataclass
class OsConfig:
    cmd_cpp_compiler: Optional[ProgramName]
    cmd_date: ProgramName
    cmd_python: ProgramName
    cmd_time: ProgramName
    cmd_timeout: ProgramName
    cmd_ulimit: ProgramName
    mem_unlimited: ProgramName

    def check_all_os_utils_exist(self) -> None:
        for cmd in (
            self.cmd_cpp_compiler,
            self.cmd_timeout,
            self.cmd_time,
            self.cmd_date,
        ):
            if cmd is not None and not shutil.which(cmd):
                warning(f"Command '{cmd}' not found, some features may not work.")


LINUX_OS_CONFIG = OsConfig(
    cmd_cpp_compiler=None,
    cmd_date="date",
    cmd_python="python3",
    cmd_time="/usr/bin/time",
    cmd_timeout="timeout",
    cmd_ulimit="ulimit",
    mem_unlimited="unlimited",
)

DARWIN_OS_CONFIG = OsConfig(
    cmd_cpp_compiler=None,
    cmd_date="gdate",
    cmd_python="python3",
    cmd_time="gtime",
    cmd_timeout="gtimeout",
    cmd_ulimit="ulimit",
    mem_unlimited="hard",
)


def find_os_config() -> OsConfig:
    if os.uname().sysname == "Linux":
        return LINUX_OS_CONFIG
    if os.uname().sysname == "Darwin":
        DARWIN_OS_CONFIG.cmd_cpp_compiler = find_macos_gcc()
        return DARWIN_OS_CONFIG
    if os.uname().sysname == "Windows":
        warning("Windows is not supported, using Linux config.")
        return LINUX_OS_CONFIG
    warning("Unknown OS, using Linux config.")
    return LINUX_OS_CONFIG


def find_pythoncmd(
    argcmd: ProgramName, alternatives: Iterable[ProgramName] = ()
) -> ProgramName:
    cmds = [argcmd] + list(alternatives) + ["python3", "python", "pypy3"]
    res = next((x for x in cmds if shutil.which(x)), "NO_PYTHON_INTERPRETER_FOUND")
    if res != argcmd:
        warning(f"Python interpreter '{argcmd}' not found, using '{res}'")
    return res


def find_macos_gcc() -> Optional[ProgramName]:
    for version in range(20, 0, -1):
        for prog in ("g++", "gcc"):
            cmd = f"{prog}-{version}"
            if shutil.which(cmd):
                return cmd
    warning("No gcc/g++ found, `make` will use its default.")
    return None
