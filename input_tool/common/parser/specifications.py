# © 2024 fezjo
from argparse import Namespace
from dataclasses import dataclass, field
from typing import Any, Type, TypeVar, Union

from input_tool.common.types import Directory, Path

ArgsGeneric = Namespace

description_sample = """
Input sample.
Given task statement, create sample input and output files.
"""
short_description_sample = "Create sample input and output files."
options_sample = [
    "help",
    "full_help",
    "indir",
    "outdir",
    "inext",
    "outext",
    "multi",
    "batchname",
    "colorful",
    "task",
]


@dataclass
class ArgsSample:
    full_help: bool
    indir: Directory
    outdir: Directory
    inext: str
    outext: str
    multi: bool
    batchname: str
    colorful: bool
    task: Union[Path, None]
    deprecated: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.indir = Path(self.indir)
        self.outdir = Path(self.outdir)
        self.task = Path(self.task) if self.task else None


description_generator = """
Input generator.
Generate inputs based on input description file. Each line is provided as input to
generator. Empty lines separate batches.
"""
short_description_generator = "Generate inputs based on input description file."
options_generator = [
    "help",
    "full_help",
    "update_check",
    "indir",
    "progdir",
    "inext",
    "compile",
    "execute",
    "colorful",
    "quiet",
    "clearinput",
    "clearbin",
    "gencmd",
    "idf_version",
    "pythoncmd_gen",
    "threads_gen",
    "description",
]


@dataclass
class ArgsGenerator:
    full_help: bool
    update_check: bool
    indir: Directory
    progdir: Directory
    inext: str
    compile: bool
    execute: bool
    colorful: bool
    quiet: bool
    clearinput: bool
    clearbin: bool
    gencmd: str
    idf_version: int
    pythoncmd: str
    threads: int
    description: Union[Path, None]
    deprecated: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.indir = Path(self.indir)
        self.progdir = Path(self.progdir)
        self.description = Path(self.description) if self.description else None


description_tester = """
Input tester.
Test all given solutions on all inputs.
By default, if outputs don't exits, use the first solution to generate them.
By default, automatically decide, how to compile and run solution.
"""
short_description_tester = "Test all given solutions on all inputs."
options_tester = [
    "help",
    "full_help",
    "indir",
    "outdir",
    "progdir",
    "inext",
    "outext",
    "tempext",
    "compile",
    "nosort",
    "dupprog",
    "bestonly",
    "execute",
    "colorful",
    "quiet",
    "nostats",
    "json",
    "cleartemp",
    "clearbin",
    "reset",
    "rustime",
    "timelimit",
    "warntimelimit",
    "memorylimit",
    "diffcmd",
    "showdiff",
    "keepwa",
    "fail_skip",
    "ioram",
    "pythoncmd_test",
    "threads_test",
    "programs",
]


@dataclass
class ArgsTester:
    full_help: bool
    indir: Directory
    outdir: Directory
    progdir: Directory
    inext: str
    outext: str
    tempext: str
    compile: bool
    sort: bool
    dupprog: bool
    bestonly: bool
    execute: bool
    colorful: bool
    quiet: bool
    stats: bool
    json: Union[Path, None]
    cleartemp: bool
    clearbin: bool
    reset: bool
    rustime: bool
    timelimit: str
    warntimelimit: str
    memorylimit: float
    diffcmd: str
    showdiff: bool
    keepwa: bool
    fail_skip: bool
    ioram: bool
    pythoncmd: str
    threads: int
    programs: list[str]
    deprecated: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.indir = Path(self.indir)
        self.outdir = Path(self.outdir)
        self.progdir = Path(self.progdir)
        self.json = Path(self.json) if self.json else None


description_compile = """
Compile programs.
Compile all given programs as if they were to be tested.
"""
short_description_compile = "Compile all given programs as if they were to be tested."
options_compile = [
    "help",
    "full_help",
    "progdir",
    "colorful",
    "quiet",
    "pythoncmd_test",
    "threads_gen",
    "programs",
]


@dataclass
class ArgsCompile:
    full_help: bool
    progdir: Directory
    colorful: bool
    quiet: bool
    pythoncmd: str
    threads: int
    programs: list[str]
    deprecated: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.progdir = Path(self.progdir)


short_description_autogenerate = "Generate inputs and outputs with one command."
description_autogenerate = """
Generate inputs and outputs with one command.
Combined generator and tester with best solution only.
"""

options_autogenerate = [
    "help",
    "full_help",
    "update_check",
    "indir",
    "outdir",
    "progdir",
    "inext",
    "outext",
    "tempext",
    "compile",
    "execute",
    "colorful",
    "quiet",
    "nostats",
    "json",
    "clearinput",
    "cleartemp",
    "clearbin",
    "gencmd",
    "idf_version",
    "pythoncmd_gen",
    "threads_gen",
    "description",
    "programs",
]


@dataclass
class ArgsAutogenerate:
    full_help: bool
    update_check: bool
    indir: Directory
    outdir: Directory
    progdir: Directory
    inext: str
    outext: str
    tempext: str
    compile: bool
    execute: bool
    colorful: bool
    quiet: bool
    stats: bool
    json: Union[Path, None]
    clearinput: bool
    cleartemp: bool
    clearbin: bool
    gencmd: str
    idf_version: int
    pythoncmd: str
    threads: int
    description: Union[Path, None]
    programs: list[str]
    deprecated: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.indir = Path(self.indir)
        self.outdir = Path(self.outdir)
        self.progdir = Path(self.progdir)
        self.json = Path(self.json) if self.json else None
        self.description = Path(self.description) if self.description else None


short_description_findlimits = (
    "Find optimal per-language timelimits from solution expectations."
)
description_findlimits = """
Find timelimits.
Determine per-language time limits so that solution batch results match
expectations encoded in filenames (e.g. sol-75-OOOT or sol-3-TLE).
Runs solutions adaptively, fastest first, to minimize total runtime.
"""

options_findlimits = [
    "help",
    "full_help",
    "indir",
    "outdir",
    "progdir",
    "inext",
    "outext",
    "tempext",
    "compile",
    "execute",
    "colorful",
    "quiet",
    "cleartemp",
    "clearbin",
    "memorylimit",
    "diffcmd",
    "baseline_multiplier",
    "max_timelimit",
    "pythoncmd_test",
    "threads_test",
    "programs",
]


@dataclass
class ArgsFindlimits:
    full_help: bool
    indir: Directory
    outdir: Directory
    progdir: Directory
    inext: str
    outext: str
    tempext: str
    compile: bool
    execute: bool
    colorful: bool
    quiet: bool
    cleartemp: bool
    clearbin: bool
    memorylimit: float
    diffcmd: str
    baseline_multiplier: float
    max_timelimit: float
    pythoncmd: str
    threads: int
    programs: list[str]
    deprecated: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.indir = Path(self.indir)
        self.outdir = Path(self.outdir)
        self.progdir = Path(self.progdir)


description_colortest = """
Test colors.
Test color support of terminal by printing all of them and exit.
"""
short_description_colortest = "Test colors by printing all of them and exit."

description_checkupdates = """
Check for updates.
Check for updates by fetching latest github release.
Print a message if a newer version is available.
"""
short_description_checkupdates = "Check for updates."


Args = Union[
    ArgsGeneric,
    ArgsSample,
    ArgsGenerator,
    ArgsTester,
    ArgsCompile,
    ArgsAutogenerate,
    ArgsFindlimits,
]

ArgsT = TypeVar(
    "ArgsT",
    ArgsSample,
    ArgsGenerator,
    ArgsTester,
    ArgsCompile,
    ArgsAutogenerate,
    ArgsFindlimits,
)


def convert_args(args: Args, to_type: Type[ArgsT], **kwargs) -> ArgsT:
    common_keys = set(args.__dict__) & set(to_type.__dataclass_fields__)
    return to_type(
        **{k: getattr(args, k) for k in common_keys},
        **kwargs,
    )
