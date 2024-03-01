# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import argparse
from dataclasses import dataclass, field
from typing import Any, Sequence, Type, TypedDict, TypeVar


def MyHelpFormatterFactory(_full_mode: bool) -> Type[argparse.HelpFormatter]:
    class MyHelpFormatter(argparse.HelpFormatter):
        # options with help message starting with this prefix are considered secondary
        # secondary options are only printed in full help mode
        # primary options in full help mode are printed in bold
        mode_prefix = "[?]"
        full_mode = _full_mode

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
                if res.endswith("\n"):
                    res = res[:-1]
                res = f"\033[1m{res}\033[0m\n"
            return res

    return MyHelpFormatter


sample_options = [
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


generator_options = [
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


tester_options = [
    "help",
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
    options: dict[str, tuple[tuple[str, ...], ParserOptions, str | None]] = {
        # actions
        "help": (
            ("-h", "--help"),
            {
                "action": "help",
                "help": "show compact help message and exit",
            },
            "actions",
        ),
        "full_help": (
            ("--help-all",),
            {
                "dest": "full_help",
                "action": "store_true",
                "help": "show help message with all the available options and exit",
            },
            "actions",
        ),
        "colortest": (
            ("--colortest",),
            {
                "dest": "colortest",
                "action": "store_true",
                "help": "[?] test colors and exit",
            },
            "actions",
        ),
        "recompile": (
            ("--recompile",),
            {
                "dest": "recompile",
                "action": "store_true",
                "help": "recompile programs and exit",
            },
            "actions",
        ),
        # naming
        "indir": (
            ("--input",),
            {
                "dest": "indir",
                "default": "test",
                "help": "[?] directory with input files (default: {})",
            },
            "naming",
        ),
        "outdir": (
            ("--output",),
            {
                "dest": "outdir",
                "default": "test",
                "help": "[?] directory for output and temporary files (default: {})",
            },
            "naming",
        ),
        "progdir": (
            ("--progdir",),
            {
                "dest": "progdir",
                "default": "prog",
                "help": "[?] directory where programs compile to, "
                'compile next to source file if set to "" (default: {})',
            },
            "naming",
        ),
        "inext": (
            ("--inext",),
            {
                "dest": "inext",
                "default": "in",
                "help": "[?] extension of input files (default: {})",
            },
            "naming",
        ),
        "outext": (
            ("--outext",),
            {
                "dest": "outext",
                "default": "out",
                "help": "[?] extension of output files (default: {})",
            },
            "naming",
        ),
        "tempext": (
            ("--tempext",),
            {
                "dest": "tempext",
                "default": "temp",
                "help": "[?] extension of temporary files (default: {})",
            },
            "naming",
        ),
        "multi": (
            ("--force-multi",),
            {
                "dest": "multi",
                "action": "store_true",
                "help": "force batch (always print .a before extension)",
            },
            "naming",
        ),
        "batchname": (
            ("--batch",),
            {
                "dest": "batchname",
                "default": "00.sample",
                "help": "[?] batch name (default: {})",
            },
            "naming",
        ),
        # preparing
        "compile": (
            ("--no-compile",),
            {
                "dest": "compile",
                "action": "store_false",
                "help": "[?] don't try to compile",
            },
            "preparing",
        ),
        "nosort": (
            ("-S", "--no-sort"),
            {
                "dest": "sort",
                "action": "store_false",
                "help": "[?] don't change order of programs",
            },
            "preparing",
        ),
        "dupprog": (
            ("--dupprog",),
            {
                "dest": "dupprog",
                "action": "store_true",
                "help": "[?] keep duplicate programs",
            },
            "preparing",
        ),
        "execute": (
            ("--execute",),
            {
                "dest": "execute",
                "action": "store_true",
                "help": "[?] treat programs as shell commands",
            },
            "preparing",
        ),
        # verbosing
        "colorful": (
            ("--boring",),
            {
                "dest": "colorful",
                "action": "store_false",
                "help": "[?] turn colors off",
            },
            "verbosing",
        ),
        "quiet": (
            ("-q", "--quiet"),
            {
                "dest": "quiet",
                "action": "store_true",
                "help": "don't let subprograms print stuff",
            },
            "verbosing",
        ),
        "nostats": (
            ("--no-statistics",),
            {
                "dest": "stats",
                "action": "store_false",
                "help": "[?] don't print statistics",
            },
            "verbosing",
        ),
        "json": (
            ("--json",),
            {
                "dest": "json",
                "default": None,
                "help": "[?] also write output in json format to file",
            },
            "verbosing",
        ),
        # cleaning
        "clearinput": (
            ("--keep-inputs",),
            {
                "dest": "clearinput",
                "action": "store_false",
                "help": "[?] don't remove old input files. Samples are never removed",
            },
            "cleaning",
        ),
        "cleartemp": (
            ("--keep-temp",),
            {
                "dest": "cleartemp",
                "action": "store_false",
                "help": "[?] don't remove temporary files after finishing",
            },
            "cleaning",
        ),
        "clearbin": (
            ("--clear-bin",),
            {
                "dest": "clearbin",
                "action": "store_true",
                "help": "[?] remove binary files after finishing",
            },
            "cleaning",
        ),
        "reset": (
            ("-R", "--Reset"),
            {
                "dest": "reset",
                "action": "store_true",
                "help": "recompute outputs, similar as `--tempext out`",
            },
            "cleaning",
        ),
        # generating
        "gencmd": (
            ("-g", "--gen"),
            {
                "dest": "gencmd",
                "default": "gen",
                "help": "generator used for generating inputs (default: {})",
            },
            "generating",
        ),
        "idf_version": (
            ("--idf-version",),
            {
                "dest": "idf_version",
                "default": 2,
                "type": int,
                "help": "idf version [1 or 2] to use (default: {})",
            },
            "generating",
        ),
        # testing
        "rustime": (
            ("--rustime",),
            {
                "dest": "rustime",
                "action": "store_true",
                "help": "[?] show Real/User/System time statistics",
            },
            "testing",
        ),
        "timelimit": (
            ("-t", "--time"),
            {
                "dest": "timelimit",
                "default": "3,cpp=1,py=5",
                "help": "set timelimit, 0 means unlimited "
                + "and can be set in per language format (default: {})",
            },
            "testing",
        ),
        "warntimelimit": (
            ("--wtime",),
            {
                "dest": "warntimelimit",
                "default": "auto",
                "help": "set tight timelimit warning time, "
                + "same format as for regular timelimit (default: {})",
            },
            "testing",
        ),
        "memorylimit": (
            ("-m", "--memory"),
            {
                "dest": "memorylimit",
                "default": 0,
                "type": float,
                "help": "set memorylimit, 0 means unlimited (default: {})",
            },
            "testing",
        ),
        "diffcmd": (
            ("-d", "--diff"),
            {
                "dest": "diffcmd",
                "default": "diff",
                "help": "program which checks correctness of output "
                + "[format: `diff $our $theirs`, `check $inp $our $theirs`, "
                + "details in TESTER.MD] (default: {})",
            },
            "testing",
        ),
        "showdiff": (
            ("-D", "--show-diff"),
            {
                "dest": "showdiff",
                "action": "store_true",
                "help": "show shortened diff output on WA",
            },
            "testing",
        ),
        "fail_skip": (
            ("-F", "--no-fail-skip"),
            {
                "dest": "fail_skip",
                "action": "store_false",
                "help": "don't skip the rest of input files in the same batch "
                + "after first fail",
            },
            "testing",
        ),
        # running
        "pythoncmd_gen": (
            ("--pythoncmd",),
            {
                "dest": "pythoncmd",
                "default": "pypy3",
                "help": "what command is used to execute python, "
                + "e.g. `python3` or `pypy3` (default: {})",
            },
            "running",
        ),
        "pythoncmd_test": (
            ("--pythoncmd",),
            {
                "dest": "pythoncmd",
                "default": "python3",
                "help": "what command is used to execute python, "
                + "e.g. `python3` or `pypy3` (default: {})",
            },
            "running",
        ),
        "threads_gen": (
            ("-j", "--threads"),
            {
                "dest": "threads",
                "default": 6,
                "type": int,
                "help": "how many threads to use (default: {})",
            },
            "running",
        ),
        "threads_test": (
            ("-j", "--threads"),
            {
                "dest": "threads",
                "default": 4,
                "type": int,
                "help": "how many threads to use (default: {})",
            },
            "running",
        ),
        # target
        "description": (
            ("description",),
            {
                "nargs": "?",
                "help": "recipe for inputs. If not provided, read it from stdin.",
            },
            None,
        ),
        "task": (
            ("task",),
            {
                "nargs": "?",
                "help": "task statement. If not provided, read it from stdin.",
            },
            None,
        ),
        "programs": (
            ("programs",),
            {
                "nargs": "*",
                "default": [],
                "help": "list of programs to be run",
            },
            None,
        ),
    }

    def __init__(self, description: str, arguments: Sequence[str]):
        self.parser = argparse.ArgumentParser(
            description=description,
            formatter_class=MyHelpFormatterFactory(False),
            add_help=False,
        )
        self.full_help_parser = argparse.ArgumentParser(
            description=description,
            formatter_class=MyHelpFormatterFactory(True),
            add_help=False,
        )
        groups = {
            "actions": self.full_help_parser.add_argument_group("actions"),
            "naming": self.full_help_parser.add_argument_group("naming"),
            "preparing": self.full_help_parser.add_argument_group("preparing"),
            "verbosing": self.full_help_parser.add_argument_group("verbosing"),
            "cleaning": self.full_help_parser.add_argument_group("cleaning"),
            "generating": self.full_help_parser.add_argument_group("generating"),
            "testing": self.full_help_parser.add_argument_group("testing"),
            "running": self.full_help_parser.add_argument_group("running"),
        }

        for arg in arguments:
            full_parser_group = self.full_help_parser
            args, kwargs, group = self.options.get(arg, (None, None, None))
            if args is None or kwargs is None:
                raise NameError(f"Unrecognized option {arg}")
            if group is not None and group:
                if group not in groups:
                    raise NameError(f"Unrecognized group {group}")
                full_parser_group = groups[group]
            if "default" in kwargs and "help" in kwargs:
                kwargs["help"] = kwargs["help"].format(kwargs["default"])
            full_parser_group.add_argument(*args, **kwargs)
            self.parser.add_argument(*args, **kwargs)

    Args = TypeVar("Args", ArgsSample, ArgsGenerator, ArgsTester)

    def parse(self, container: Type[Args]) -> Args:
        self.args = self.parser.parse_args()
        if self.args.full_help:
            self.full_help_parser.print_help()
            quit(0)
        return container(**vars(self.args))
