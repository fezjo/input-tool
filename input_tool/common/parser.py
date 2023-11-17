# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import argparse
from dataclasses import dataclass, field
from typing import Any, Sequence, Type, TypedDict, TypeVar


@dataclass
class ArgsSample:
    indir: str
    outdir: str
    inext: str
    outext: str
    batchname: str
    multi: bool
    colorful: bool
    task: str | None
    deprecated: list[Any] = field(default_factory=list)


@dataclass
class ArgsGenerator:
    indir: str
    progdir: str
    inext: str
    compile: bool
    execute: bool
    pythoncmd: str
    colorful: bool
    quiet: bool
    clearbin: bool
    clearinput: bool
    description: str
    gencmd: str
    threads: int
    deprecated: list[Any] = field(default_factory=list)


@dataclass
class ArgsTester:
    indir: str
    outdir: str
    progdir: str
    inext: str
    outext: str
    tempext: str
    reset: bool
    timelimit: str
    warntimelimit: str
    memorylimit: float
    diffcmd: str | None
    showdiffoutput: bool
    fskip: bool
    dupprog: bool
    rustime: bool
    compile: bool
    sort: bool
    execute: bool
    pythoncmd: str
    threads: int
    colorful: bool
    colortest: bool
    quiet: bool
    stats: bool
    json: str | None
    cleartemp: bool
    clearbin: bool
    programs: list[str]
    inside_oneline: bool = field(default=False)
    inside_inputmaxlen: int = field(default=0)
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
        # file names
        "indir": (
            ("-i", "--input"),
            {
                "dest": "indir",
                "default": "test",
                "help": "directory with input files (default=test)",
            },
        ),
        "outdir": (
            ("-o", "--output"),
            {
                "dest": "outdir",
                "default": "test",
                "help": "directory for output and temporary files (default=test)",
            },
        ),
        "progdir": (
            ("-p", "--progdir"),
            {
                "dest": "progdir",
                "default": "prog",
                "help": "directory where programs compile to (default=prog), "
                'compile next to source file if set to ""',
            },
        ),
        "inext": (
            ("-I",),
            {
                "dest": "inext",
                "default": "in",
                "help": "extension of input files (default=in)",
            },
        ),
        "outext": (
            ("-O",),
            {
                "dest": "outext",
                "default": "out",
                "help": "extension of output files (default=out)",
            },
        ),
        "tempext": (
            ("-T",),
            {
                "dest": "tempext",
                "default": "temp",
                "help": "extension of temporary files (default=temp)",
            },
        ),
        "reset": (
            ("-R", "--Reset"),
            {
                "dest": "reset",
                "action": "store_true",
                "help": "recompute outputs, similar as -T out",
            },
        ),
        "batchname": (
            ("-b", "--batch"),
            {
                "dest": "batchname",
                "default": "00.sample",
                "help": "batch name (default=00.sample)",
            },
        ),
        "multi": (
            ("-m", "--force-multi"),
            {
                "dest": "multi",
                "action": "store_true",
                "help": "force batch (always print .a before extension)",
            },
        ),
        # testing options
        "timelimit": (
            ("-t", "--time"),
            {
                "dest": "timelimit",
                "default": "3,cpp=1,py=5",
                "help": "set timelimit (default=3,cpp=1,py=5), "
                + "can be set to unlimited using 0 and "
                + 'optionally in per language format (e.g. "1.5,py=0,cpp=0.5")',
            },
        ),
        "warntimelimit": (
            ("--wtime",),
            {
                "dest": "warntimelimit",
                "default": "auto",
                "help": "set warning tight timelimit (default=auto), "
                + "which issues warning but does not fail, can be set in "
                + 'optional per language format (e.g. "0.5,py=1.5,cpp=0.15")',
            },
        ),
        "memorylimit": (
            ("-m", "--memory"),
            {
                "dest": "memorylimit",
                "help": "set memorylimit (default=infinity)",
                "default": 0,
                "type": float,
            },
        ),
        "wrapper": (
            ("-w", "--wrapper"),
            {
                "dest": "wrapper",
                "nargs": "?",
                "default": False,
                "metavar": "PATH",
                "help": 'use wrapper, default PATH="$WRAPPER"',
            },
        ),
        "diffcmd": (
            ("-d", "--diff"),
            {
                "dest": "diffcmd",
                "default": None,
                "help": "program which checks correctness of output (default=diff), "
                + "arguments given to program depends of prefix:"
                + "       diff $our $theirs,"
                + "       check $inp $our $theirs,"
                + "       ch_ito $inp $theirs $our,"
                + "       test $dir $name $i $o $t",
            },
        ),
        "showdiffoutput": (
            (
                "-D",
                "--show-diff-output",
            ),
            {
                "dest": "showdiffoutput",
                "action": "store_true",
                "help": "show shortened diff output on WA",
            },
        ),
        "fskip": (
            (
                "-F",
                "--no-fskip",
            ),
            {
                "dest": "fskip",
                "action": "store_false",
                "help": "dont skip the rest of input files in the same batch "
                + "after first fail",
            },
        ),
        "dupprog": (
            ("--dupprog",),
            {
                "dest": "dupprog",
                "action": "store_true",
                "help": "keep duplicate programs",
            },
        ),
        "rustime": (
            ("--rustime",),
            {
                "dest": "rustime",
                "action": "store_true",
                "help": "show Real/User/System time statistics",
            },
        ),
        # running options
        "compile": (
            ("--no-compile",),
            {"dest": "compile", "action": "store_false", "help": "dont try to compile"},
        ),
        "nosort": (
            (
                "-S",
                "--no-sort",
            ),
            {
                "dest": "sort",
                "action": "store_false",
                "help": "dont change order of programs",
            },
        ),
        "execute": (
            ("-x", "--execute"),
            {
                "dest": "execute",
                "action": "store_true",
                "help": "treat programs as bash commands. Dont try to do "
                + "as compiling",
            },
        ),
        "pythoncmd_gen": (
            ("--pythoncmd",),
            {
                "dest": "pythoncmd",
                "default": "pypy3",
                "help": "what command is used to execute python, "
                + "e.g. `python3` or `pypy3` (default=pypy3)",
            },
        ),
        "pythoncmd_test": (
            ("--pythoncmd",),
            {
                "dest": "pythoncmd",
                "default": "python3",
                "help": "what command is used to execute python, "
                + "e.g. `python3` or `pypy3` (default=python3)",
            },
        ),
        "threads_gen": (
            ("-j", "--threads"),
            {
                "dest": "threads",
                "default": 6,
                "help": "how many threads to use (default=6)",
                "type": int,
            },
        ),
        "threads_test": (
            ("-j", "--threads"),
            {
                "dest": "threads",
                "default": 4,
                "help": "how many threads to use (default=4)",
                "type": int,
            },
        ),
        # verbosing
        "colorful": (
            ("-B", "--boring"),
            {"dest": "colorful", "action": "store_false", "help": "turn colors off"},
        ),
        "colortest": (
            ("--colortest",),
            {
                "dest": "colortest",
                "action": "store_true",
                "help": "test colors and exit",
            },
        ),
        "quiet": (
            ("-q", "--quiet"),
            {
                "dest": "quiet",
                "action": "store_true",
                "help": "dont let subprograms print stuff",
            },
        ),
        "Quiet": (
            ("-Q", "--Quiet"),
            {"dest": "Quiet", "action": "store_true", "help": "dont print anything"},
        ),
        "stats": (
            ("-s", "--statistics"),
            {
                "dest": "deprecated",
                "action": "append_const",
                "const": "statistics (-s --statistics)",
                "help": "print statistics (deprecated)",
            },
        ),
        "nostats": (
            ("--no-statistics",),
            {"dest": "stats", "action": "store_false", "help": "dont print statistics"},
        ),
        "json": (
            ("--json",),
            {
                "dest": "json",
                "default": None,
                "help": "also write output in json format to file",
            },
        ),
        # cleanup
        "cleartemp": (
            ("-k", "--keep-temp"),
            {
                "dest": "cleartemp",
                "action": "store_false",
                "help": "dont remove temporary files after finishing",
            },
        ),
        "noclearbin": (
            ("-K", "--keep-bin"),
            {
                "dest": "deprecated",
                "action": "append_const",
                "const": "noclearbin (-K --keep-bin)",
                "help": "dont remove binary files after finishing (deprecated)",
            },
        ),
        "clearbin": (
            ("--clear-bin",),
            {
                "dest": "clearbin",
                "action": "store_true",
                "help": "remove binary files after finishing",
            },
        ),
        "clearinput": (
            ("-k", "--keep-inputs"),
            {
                "dest": "clearinput",
                "action": "store_false",
                "help": "dont remove old input files. Samples are never removed",
            },
        ),
        # what to do
        "programs": (
            ("programs",),
            {"nargs": "+", "help": "list of programs to be run"},
        ),
        "description": (
            ("description",),
            {
                "nargs": "?",
                "help": "recipe for inputs. If not provided, read it from stdin.",
            },
        ),
        "gencmd": (
            ("-g", "--gen"),
            {
                "dest": "gencmd",
                "default": "gen",
                "help": "generator used for generating inputs (default=gen)",
            },
        ),
        "task": (
            ("task",),
            {
                "nargs": "?",
                "help": "task statement. If not provided, read it from stdin.",
            },
        ),
    }

    def __init__(self, description: str, arguments: Sequence[str]):
        self.parser = argparse.ArgumentParser(description=description)
        for arg in arguments:
            args, kwargs = self.options.get(arg, (None, None))
            if args is None or kwargs is None:
                raise NameError(f"Unrecognized option {arg}")
            self.parser.add_argument(*args, **kwargs)

    Args = TypeVar("Args", ArgsSample, ArgsGenerator, ArgsTester)

    def parse(self, container: Type[Args]) -> Args:
        self.args = self.parser.parse_args()
        return container(**vars(self.args))
