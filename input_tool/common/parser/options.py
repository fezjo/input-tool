# © 2024 fezjo
from typing import Any, Type, TypedDict


class ParserOptions(TypedDict, total=False):
    action: str
    const: Any
    dest: str
    default: Any
    help: str
    metavar: str
    nargs: str
    type: Type[Any]


argument_options: dict[str, tuple[tuple[str, ...], ParserOptions, str | None]] = {
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
    # naming
    "indir": (
        ("--input",),
        {
            "dest": "indir",
            "default": "test",
            "metavar": "DIR",
            "help": "[?] directory with input files (default: {})",
        },
        "naming",
    ),
    "outdir": (
        ("--output",),
        {
            "dest": "outdir",
            "default": "test",
            "metavar": "DIR",
            "help": "[?] directory for output and temporary files (default: {})",
        },
        "naming",
    ),
    "progdir": (
        ("--progdir",),
        {
            "dest": "progdir",
            "default": "prog",
            "metavar": "DIR",
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
            "metavar": "EXT",
            "help": "[?] extension of input files (default: {})",
        },
        "naming",
    ),
    "outext": (
        ("--outext",),
        {
            "dest": "outext",
            "default": "out",
            "metavar": "EXT",
            "help": "[?] extension of output files (default: {})",
        },
        "naming",
    ),
    "tempext": (
        ("--tempext",),
        {
            "dest": "tempext",
            "default": "temp",
            "metavar": "EXT",
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
            "metavar": "NAME",
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
    "bestonly": (
        ("--best-only",),
        {
            "dest": "bestonly",
            "action": "store_true",
            "help": "keep only the best program to generate ouputs",
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
            "metavar": "NUM",
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
            "metavar": "LIMIT",
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
            "metavar": "LIMIT",
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
            "metavar": "MB",
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
    "ioram": (
        ("--ioram",),
        {
            "dest": "ioram",
            "action": "store_true",
            "help": "[?] run programs in ramdisk",
        },
        "testing",
    ),
    # running
    "pythoncmd_gen": (
        ("--pythoncmd",),
        {
            "dest": "pythoncmd",
            "default": "pypy3",
            "metavar": "CMD",
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
            "metavar": "CMD",
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
            "metavar": "NUM",
            "help": "how many threads to use (default: {})",
        },
        "running",
    ),
    "threads_test": (
        ("-j", "--threads"),
        {
            "dest": "threads",
            "default": 2,
            "type": int,
            "metavar": "NUM",
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
