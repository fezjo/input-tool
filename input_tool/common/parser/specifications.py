from dataclasses import dataclass, field
from typing import Any

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
    indir: str
    outdir: str
    inext: str
    outext: str
    multi: bool
    batchname: str
    colorful: bool
    task: str | None
    deprecated: list[Any] = field(default_factory=list)


description_generator = """
Input generator.
Generate inputs based on input description file. Each line is provided as input to
generator. Empty lines separate batches.
"""
short_description_generator = "Generate inputs based on input description file."
options_generator = [
    "help",
    "full_help",
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
    indir: str
    progdir: str
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
    description: str
    deprecated: list[Any] = field(default_factory=list)


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
    "fail_skip",
    "pythoncmd_test",
    "threads_test",
    "programs",
]


@dataclass
class ArgsTester:
    full_help: bool
    indir: str
    outdir: str
    progdir: str
    inext: str
    outext: str
    tempext: str
    compile: bool
    sort: bool
    dupprog: bool
    execute: bool
    colorful: bool
    quiet: bool
    stats: bool
    json: str | None
    cleartemp: bool
    clearbin: bool
    reset: bool
    rustime: bool
    timelimit: str
    warntimelimit: str
    memorylimit: float
    diffcmd: str
    showdiff: bool
    fail_skip: bool
    pythoncmd: str
    threads: int
    programs: list[str]
    deprecated: list[Any] = field(default_factory=list)


description_compile = """
Compile programs.
Compile all given programs as if they were to be tested.
"""
short_description_compile = "Compile all given programs as if they were to be tested."
options_compile = [
    "help",
    "full_help",
    "threads_test",
    "programs",
]


@dataclass
class ArgsCompile:
    full_help: bool
    threads: int
    programs: list[str]
    deprecated: list[Any] = field(default_factory=list)


description_colortest = """
Test colors and exit.
"""
short_description_colortest = "Test colors and exit."
options_colortest = [
    "help",
]


@dataclass
class ArgsColorTest:
    deprecated: list[Any] = field(default_factory=list)