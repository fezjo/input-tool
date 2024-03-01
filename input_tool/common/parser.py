# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import argparse
from dataclasses import dataclass, field
from typing import Any, Sequence, Type, TypedDict, TypeVar


class MyHelpFormatter(argparse.HelpFormatter):
    # options with help message starting with this prefix are considered secondary
    # secondary options are only printed in full help mode
    # primary options in full help mode are printed in bold
    mode_prefix = "[?]"
    full_mode = False

    def _format_action(self, action):
        if action.help is None:
            return super()._format_action(action)
        orig_help = action.help
        issecondary = action.help.startswith(self.mode_prefix)
        if issecondary:
            action.help = action.help.removeprefix(self.mode_prefix).strip()
        res = ""
        if self.full_mode or not issecondary:
            res = super()._format_action(action)
        action.help = orig_help
        if self.full_mode and not issecondary:
            res = f"\033[1m{res}\033[0m"
        return res


sample_options = [
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


generator_options = [
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


tester_options = [
    "full_help",
    "colortest",
    "recompile",
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
    colortest: bool
    recompile: bool
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


class ParserOptions(TypedDict, total=False):
    action: str
    const: Any
    dest: str
    default: Any
    help: str
    metavar: str
    nargs: str
    type: Type[Any]


class Parser:
    options: dict[str, tuple[tuple[str, ...], ParserOptions]] = {
        # actions
        "full_help": (
            ("--help-all",),
            {
                "dest": "full_help",
                "action": "store_true",
                "help": "show help message with all the available options and exit",
            },
        ),
        "colortest": (
            ("--colortest",),
            {
                "dest": "colortest",
                "action": "store_true",
                "help": "[?] test colors and exit",
            },
        ),
        "recompile": (
            ("--recompile",),
            {
                "dest": "recompile",
                "action": "store_true",
                "help": "recompile programs and exit",
            },
        ),
        # file names
        "indir": (
            ("--input",),
            {
                "dest": "indir",
                "default": "test",
                "help": "[?] directory with input files (default: {})",
            },
        ),
        "outdir": (
            ("--output",),
            {
                "dest": "outdir",
                "default": "test",
                "help": "[?] directory for output and temporary files (default: {})",
            },
        ),
        "progdir": (
            ("--progdir",),
            {
                "dest": "progdir",
                "default": "prog",
                "help": "[?] directory where programs compile to, "
                'compile next to source file if set to "" (default: {})',
            },
        ),
        "inext": (
            ("--inext",),
            {
                "dest": "inext",
                "default": "in",
                "help": "[?] extension of input files (default: {})",
            },
        ),
        "outext": (
            ("--outext",),
            {
                "dest": "outext",
                "default": "out",
                "help": "[?] extension of output files (default: {})",
            },
        ),
        "tempext": (
            ("--tempext",),
            {
                "dest": "tempext",
                "default": "temp",
                "help": "[?] extension of temporary files (default: {})",
            },
        ),
        "multi": (
            ("--force-multi",),
            {
                "dest": "multi",
                "action": "store_true",
                "help": "force batch (always print .a before extension)",
            },
        ),
        "batchname": (
            ("--batch",),
            {
                "dest": "batchname",
                "default": "00.sample",
                "help": "[?] batch name (default: {})",
            },
        ),
        # prepare options
        "compile": (
            ("--no-compile",),
            {
                "dest": "compile",
                "action": "store_false",
                "help": "[?] don't try to compile",
            },
        ),
        "nosort": (
            ("-S", "--no-sort"),
            {
                "dest": "sort",
                "action": "store_false",
                "help": "[?] don't change order of programs",
            },
        ),
        "dupprog": (
            ("--dupprog",),
            {
                "dest": "dupprog",
                "action": "store_true",
                "help": "[?] keep duplicate programs",
            },
        ),
        "execute": (
            ("--execute",),
            {
                "dest": "execute",
                "action": "store_true",
                "help": "[?] treat programs as shell commands",
            },
        ),
        # verbosing
        "colorful": (
            ("--boring",),
            {
                "dest": "colorful",
                "action": "store_false",
                "help": "[?] turn colors off",
            },
        ),
        "quiet": (
            ("-q", "--quiet"),
            {
                "dest": "quiet",
                "action": "store_true",
                "help": "don't let subprograms print stuff",
            },
        ),
        "nostats": (
            ("--no-statistics",),
            {
                "dest": "stats",
                "action": "store_false",
                "help": "[?] don't print statistics",
            },
        ),
        "json": (
            ("--json",),
            {
                "dest": "json",
                "default": None,
                "help": "[?] also write output in json format to file",
            },
        ),
        # cleanup
        "clearinput": (
            ("--keep-inputs",),
            {
                "dest": "clearinput",
                "action": "store_false",
                "help": "[?] don't remove old input files. Samples are never removed",
            },
        ),
        "cleartemp": (
            ("--keep-temp",),
            {
                "dest": "cleartemp",
                "action": "store_false",
                "help": "[?] don't remove temporary files after finishing",
            },
        ),
        "clearbin": (
            ("--clear-bin",),
            {
                "dest": "clearbin",
                "action": "store_true",
                "help": "[?] remove binary files after finishing",
            },
        ),
        "reset": (
            ("-R", "--Reset"),
            {
                "dest": "reset",
                "action": "store_true",
                "help": "recompute outputs, similar as `--tempext out`",
            },
        ),
        # generating options
        "gencmd": (
            ("-g", "--gen"),
            {
                "dest": "gencmd",
                "default": "gen",
                "help": "generator used for generating inputs (default: {})",
            },
        ),
        "idf_version": (
            ("--idf-version",),
            {
                "dest": "idf_version",
                "default": 2,
                "type": int,
                "help": "idf version [1 or 2] to use (default: {})",
            },
        ),
        # testing options
        "rustime": (
            ("--rustime",),
            {
                "dest": "rustime",
                "action": "store_true",
                "help": "[?] show Real/User/System time statistics",
            },
        ),
        "timelimit": (
            ("-t", "--time"),
            {
                "dest": "timelimit",
                "default": "3,cpp=1,py=5",
                "help": "set timelimit, 0 means unlimited "
                + "and can be set in per language format (default: {})",
            },
        ),
        "warntimelimit": (
            ("--wtime",),
            {
                "dest": "warntimelimit",
                "default": "auto",
                "help": "set tight timelimit warning time, "
                + "same format as for regular timelimit (default: {})",
            },
        ),
        "memorylimit": (
            ("-m", "--memory"),
            {
                "dest": "memorylimit",
                "default": 0,
                "type": float,
                "help": "set memorylimit, 0 means unlimited (default: {})",
            },
        ),
        "diffcmd": (
            ("-d", "--diff"),
            {
                "dest": "diffcmd",
                "default": "diff",
                "help": "program which checks correctness of output [format: "
                + "`diff $our $theirs`, `check $inp $our $theirs`, rest in TESTER.MD] "
                + "(default: {})",
            },
        ),
        "showdiff": (
            ("-D", "--show-diff"),
            {
                "dest": "showdiff",
                "action": "store_true",
                "help": "show shortened diff output on WA",
            },
        ),
        "fail_skip": (
            ("-F", "--no-fail-skip"),
            {
                "dest": "fail_skip",
                "action": "store_false",
                "help": "don't skip the rest of input files in the same batch "
                + "after first fail",
            },
        ),
        # running options
        "pythoncmd_gen": (
            ("--pythoncmd",),
            {
                "dest": "pythoncmd",
                "default": "pypy3",
                "help": "what command is used to execute python, "
                + "e.g. `python3` or `pypy3` (default: {})",
            },
        ),
        "pythoncmd_test": (
            ("--pythoncmd",),
            {
                "dest": "pythoncmd",
                "default": "python3",
                "help": "what command is used to execute python, "
                + "e.g. `python3` or `pypy3` (default: {})",
            },
        ),
        "threads_gen": (
            ("-j", "--threads"),
            {
                "dest": "threads",
                "default": 6,
                "type": int,
                "help": "how many threads to use (default: {})",
            },
        ),
        "threads_test": (
            ("-j", "--threads"),
            {
                "dest": "threads",
                "default": 4,
                "type": int,
                "help": "how many threads to use (default: {})",
            },
        ),
        # what to do
        "description": (
            ("description",),
            {
                "nargs": "?",
                "help": "recipe for inputs. If not provided, read it from stdin.",
            },
        ),
        "task": (
            ("task",),
            {
                "nargs": "?",
                "help": "task statement. If not provided, read it from stdin.",
            },
        ),
        "programs": (
            ("programs",),
            {
                "nargs": "*",
                "default": [],
                "help": "list of programs to be run",
            },
        ),
    }

    def __init__(self, description: str, arguments: Sequence[str]):
        self.parser = argparse.ArgumentParser(
            description=description, formatter_class=MyHelpFormatter
        )
        for arg in arguments:
            args, kwargs = self.options.get(arg, (None, None))
            if args is None or kwargs is None:
                raise NameError(f"Unrecognized option {arg}")
            if "default" in kwargs and "help" in kwargs:
                kwargs["help"] = kwargs["help"].format(kwargs["default"])
            self.parser.add_argument(*args, **kwargs)

    Args = TypeVar("Args", ArgsSample, ArgsGenerator, ArgsTester)

    def parse(self, container: Type[Args]) -> Args:
        self.args = self.parser.parse_args()
        if self.args.full_help:
            MyHelpFormatter.full_mode = True
            self.parser.print_help()
            quit(0)
        return container(**vars(self.args))
