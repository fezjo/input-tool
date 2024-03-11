# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
"""
Basic behaviour you need to understand if you want to use this.
Don't use spaces in file names.

Naming conventions -- Type of file is determined by prefix.
  gen - generator  -- Gets one line on stdin, prints input on stdout.
  sol - solution   -- Gets input on stdin, prints output on stdout.
                      Can be restricted by time and memory.
                      Stderr is ignored.
  val - validator  -- Gets input on stdin, prints one line (optional)
                      and returns 0 (good input) / 1 (bad input).
                      Also gets input name as arguments split by '.',
                      example: ./validator 00 sample a in < 00.sample.a.in
  diff, check, ch_ito_, test - checker
                   -- Gets arguments with names of files.
  <other>          -- Anything. E.g. you can use arbitrary program as generator,
                      but dont use sol*, val*, diff*, ...
  Split parts of names by '-' not '_'.
  In solutions, parts can be score, author, algorithm, complexity
  in this order. E.g. sol-100-jano-n2.cpp, sol-jano.cpp, sol-40.cpp
  (if second part is an integer, it is treated as score).

Program types      -- What is recognized and smartly processed.
                      It is determined mainly by extension and number of words.
  multiple words   -- Run as it is.
  noextension      -- Check if binary should be compiled and maybe compile.
                      Then run ./noextension if file exists and noextension otherwise.
program.ext      -- If c/cc/c++/pas/java, compile and run binary.
program.ext      -- If .pyX, run as 'pythonX program.ext. py = py3

"""

import os
from datetime import timedelta
from enum import Enum
from typing import Iterable, Optional, Union

from input_tool.common.messages import table_header
from input_tool.common.os_config import OsConfig


def is_file_newer(file1: str, file2: str) -> bool | None:
    if not os.path.exists(file1) or not os.path.exists(file2):
        return None
    return os.path.getctime(file1) > os.path.getctime(file2)


def to_base_alnum(s: str) -> str:
    s = s.split("/")[-1]
    return "".join([x for x in s if str.isalnum(x)])


class Langs:
    class Lang(Enum):
        unknown = None
        c = "c"
        cpp = "cpp"
        pascal = "pas"
        java = "java"
        python = "py3"
        rust = "rs"

    lang_compiled = (Lang.c, Lang.cpp, Lang.pascal, Lang.java, Lang.rust)
    lang_script = (Lang.python,)
    lang_all = lang_compiled + lang_script

    ext: dict[Lang, list[str]] = {
        Lang.unknown: [],
        Lang.c: ["c"],
        Lang.cpp: ["cpp", "cxx", "c++", "cp", "cc"],
        Lang.pascal: ["pas"],
        Lang.java: ["java"],
        Lang.python: ["py"],
        Lang.rust: ["rs"],
    }

    expected_performance_ranking = (
        Lang.cpp,
        Lang.rust,
        Lang.c,
        Lang.java,
        Lang.pascal,
        Lang.python,
        Lang.unknown,
    )

    @staticmethod
    def from_filename(filename: str) -> Lang:
        ext = filename.rsplit(".", 1)[-1]
        return Langs.from_ext(ext)

    @staticmethod
    def from_ext(ext: Union[str, None]) -> Lang:
        for lang in Langs.Lang:
            if ext in Langs.ext[lang]:
                return lang
        return Langs.Lang.unknown

    @staticmethod
    def collect_exts(langs: Iterable[Lang]) -> set[str]:
        return set(ext for lang in langs for ext in Langs.ext[lang])


class Config:
    Timelimit = dict[Union[Langs.Lang, str], timedelta]

    fail_skip: bool
    rus_time: bool
    timelimits: Timelimit = {Langs.Lang.unknown: timedelta(seconds=3)}
    warn_timelimits: Timelimit = {Langs.Lang.unknown: timedelta(0)}
    memorylimit: float
    quiet: bool
    compile: bool
    execute: bool
    inside_oneline: bool
    inside_inputmaxlen: int
    progdir: Optional[str] = None
    cmd_maxlen: int = len("Solution")
    os_config: OsConfig

    @staticmethod
    def get_timelimit(
        timelimits: Timelimit, ext: Optional[str], lang: Optional[Langs.Lang]
    ) -> timedelta:
        if ext in timelimits:
            return timelimits[ext]
        if lang in timelimits:
            return timelimits[lang]
        return timelimits[Langs.Lang.unknown]


def get_statistics_header(inputs: Iterable[str]) -> str:
    batches = set([x.rsplit(".", 2)[0] for x in inputs if "sample" not in x])
    pts = len(batches)
    widths = [Config.cmd_maxlen, 8, 9, 6, 6, max(7, pts)]
    colnames = ["Solution", "Max time", "Times sum", f"Pt {pts:3}", "Status", "Batches"]
    return table_header(colnames, widths, "<>>>><")


"""
# compile the wrapper if turned on
wrapper_binary = None
if args.wrapper != False:
    path = args.wrapper or "$WRAPPER"
    if os.uname()[-1] == "x86_64":
        wrapper_source = f"{path}/wrapper-mj-amd64.c"
    else:
        wrapper_source = f"{path}/wrapper-mj-x86.c"
    wrapper_binary = f"{path}/wrapper"
    if os.system(f"gcc -O2 -o {wrapper_binary} {wrapper_source}"):
        fatal("Wrapper compile failed.")
"""
