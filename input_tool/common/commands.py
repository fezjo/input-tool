# (c) 2014 jano <janoh@ksp.sk>
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

from __future__ import annotations
import os
import shutil
import subprocess
from collections import defaultdict
from input_tool.common.messages import *
from typing import Iterable, Sequence, Tuple
from dataclasses import dataclass

from input_tool.common.parser import ArgsGenerator, ArgsTester

Args = ArgsGenerator | ArgsTester


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
        python2 = "py2"
        python3 = "py3"
        rust = "rs"

    lang_compiled = (Lang.c, Lang.cpp, Lang.pascal, Lang.java, Lang.rust)
    lang_script = (Lang.python2, Lang.python3)
    lang_all = lang_compiled + lang_script

    ext = {
        Lang.unknown: [],
        Lang.c: ["c"],
        Lang.cpp: ["cpp", "cxx", "c++", "cp", "cc"],
        Lang.pascal: ["pas"],
        Lang.java: ["java"],
        Lang.python3: ["py", "py3"],
        Lang.python2: ["py2"],
        Lang.rust: ["rs"],
    }

    @staticmethod
    def from_ext(ext: str | None) -> Lang:
        for lang in Langs.Lang:
            if ext in Langs.ext[lang]:
                return lang
        return Langs.Lang.unknown

    @staticmethod
    def collect_exts(langs: Iterable[Lang]) -> set[str]:
        return set(ext for lang in langs for ext in Langs.ext[lang])


class Config:
    timelimits: dict[Langs.Lang | str, float] = {Langs.Lang.unknown: 0}
    warn_timelimits: dict[Langs.Lang | str, float] = {Langs.Lang.unknown: 0}
    python_exec = "python"


class Program:
    def compare_mask(self) -> Tuple[int, int, str]:
        return (0, 0, self.name)

    def __lt__(self, other: Program) -> bool:
        return self.compare_mask() < other.compare_mask()

    def _transform(self) -> None:
        self.compilecmd = None
        self.source = None
        self.ext = None
        self.run_cmd = self.name
        self.filestoclear: list[str] = []
        self.lang: Langs.Lang = Langs.Lang.unknown

        # if it is final command, dont do anything
        if self.forceexecute or len(self.name.split()) > 1:
            return

        # compute source, binary and extension
        # TODO: base self.name can have multiple sources
        if not "." in self.name:
            valid: list[str] = []
            for ext_category in (Langs.lang_compiled, Langs.lang_script):
                for ext in Langs.collect_exts(ext_category):
                    if os.path.exists(self.name + "." + ext):
                        valid.append(ext)
            if valid:
                self.ext = valid[0]
                self.source = self.name + "." + self.ext
                if os.path.exists(self.name):
                    valid.append("<noextension>")
            if len(valid) > 1:
                warning(
                    "Warning: multiple possible sources for %s, using first %s"
                    % (self.name, valid)
                )
        else:
            self.source = self.name
            self.run_cmd, self.ext = self.name.rsplit(".", 1)

        self.lang = Langs.from_ext(self.ext)
        if self.lang is Langs.Lang.unknown or not self.source:
            self.run_cmd = self.name
            return

        # compute run_cmd
        if self.lang in Langs.lang_script:
            self.run_cmd = self.source

        docompile = (
            self.cancompile
            and self.lang in Langs.lang_compiled
            and (
                self.source == self.name
                or not os.path.exists(self.run_cmd)
                or is_file_newer(self.source, self.run_cmd)
            )
        )
        if docompile:
            if self.lang is Langs.Lang.c:
                self.compilecmd = 'CFLAGS="$CFLAGS -O2 -std=c17" make %s' % self.run_cmd
                self.filestoclear.append(self.run_cmd)
            elif self.lang is Langs.Lang.cpp:
                self.compilecmd = (
                    'CXXFLAGS="$CXXFLAGS -O2 -std=c++20" make %s' % self.run_cmd
                )
                self.filestoclear.append(self.run_cmd)
            elif self.lang is Langs.Lang.pascal:
                self.compilecmd = "fpc -o%s %s" % (self.run_cmd, self.source)
                self.filestoclear.append(self.run_cmd)
                self.filestoclear.append(self.run_cmd + ".o")
            elif self.lang is Langs.Lang.java:
                class_dir = ".classdir-%s-%s.tmp" % (
                    to_base_alnum(self.name),
                    os.getpid(),
                )
                os.mkdir(class_dir)
                self.compilecmd = "javac %s -d %s" % (self.source, class_dir)
                self.filestoclear.append(class_dir)
                self.run_cmd = "-cp %s %s" % (class_dir, self.run_cmd)
            elif self.lang is Langs.Lang.rust:
                self.compilecmd = "rustc -C opt-level=2 %s.rs" % self.run_cmd
                self.filestoclear.append(self.run_cmd)

        if not os.access(self.run_cmd, os.X_OK):
            if self.lang is Langs.Lang.python3:
                self.run_cmd = "%s3 %s" % (Config.python_exec, self.source)
            if self.lang is Langs.Lang.python2:
                self.run_cmd = "%s2 %s" % (Config.python_exec, self.source)
            if self.lang is Langs.Lang.java:
                self.run_cmd = "java -Xss256m " + self.run_cmd

    def prepare(self) -> None:
        if self.compilecmd != None:
            so = subprocess.PIPE if self.quiet else None
            se = subprocess.STDOUT if self.quiet else None
            infob("Compiling: %s" % self.compilecmd)
            try:
                subprocess.check_call(self.compilecmd, shell=True, stdout=so, stderr=se)
            except:
                error("Compilation failed.")

        assert self.run_cmd
        if (
            not self.forceexecute
            and os.access(self.run_cmd, os.X_OK)
            and self.run_cmd[0].isalnum()
        ):
            self.run_cmd = "./" + self.run_cmd

        if isinstance(self, Solution):
            Solution.cmd_maxlen = max(Solution.cmd_maxlen, len(self.run_cmd))
        self.ready = True

    def clear_files(self) -> None:
        for f in self.filestoclear:
            if os.path.exists(f):
                if os.path.isdir(f):
                    shutil.rmtree(f)
                else:
                    os.remove(f)
            else:
                warning("Not found %s" % f)

    def __init__(self, name: str, args: Args):
        self.name = name
        self.quiet: bool = args.quiet
        self.cancompile: bool = args.compile
        self.forceexecute: bool = args.execute
        self.ready = False

        # compute run_cmd, compilecmd and filestoclear
        self._transform()


class Solution(Program):
    @dataclass
    class Statistics:
        maxtime: float
        sumtime: float
        batchresults: dict[str, Status]
        result: Status
        times: defaultdict[str, list[tuple[float]]]
        failedbatches: set[str]

    cmd_maxlen = len("Solution")

    @staticmethod
    def filename_befits(filename: str) -> bool:
        return to_base_alnum(filename).startswith("sol")

    def updated_status(self, original: Status, new: Status) -> Status:
        if original == Status.ok:
            return new
        if new == Status.ok:
            return original
        if original == Status.err or new == Status.err:
            return Status.err
        return original

    def compare_mask(self) -> Tuple[int, int, str]:
        filename = self.name.rsplit(" ", 1)[-1].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        score = 0
        parts = filename.split("-")
        if "vzorak" in parts or "vzor" in parts:
            score += 2000
        if filename.startswith("sol"):
            if len(filename) == 3:
                score += 1000
            if len(parts) > 1 and parts[1].isnumeric():
                score += int(parts[1])
        return (-1, -score, self.name)

    def __init__(self, name: str, args: Args):
        super().__init__(name, args)
        self.statistics = Solution.Statistics(
            maxtime=-1,
            sumtime=0,
            batchresults={},
            result=Status.ok,
            times=defaultdict(list),
            failedbatches=set(),
        )

    @staticmethod
    def get_statistics_header(inputs: Iterable[str]) -> str:
        batches = set([x.rsplit(".", 2)[0] for x in inputs if not "sample" in x])
        pts = len(batches)
        widths = [Solution.cmd_maxlen, 8, 9, 6, 6]
        colnames = ["Solution", "Max time", "Times sum", "Pt %3d" % pts, "Status"]
        return table_header(colnames, widths, [-1, 1, 1, 1, 0])

    def get_statistics(self) -> str:
        points, maxpoints = 0, 0
        for batch in self.statistics.batchresults:
            if "sample" in batch:
                continue
            maxpoints += 1
            if self.statistics.batchresults[batch] == Status.ok:
                points += 1
                self.statistics.maxtime = max(
                    self.statistics.maxtime,
                    max(map(lambda ts: ts[0], self.statistics.times[batch])),
                )
        color = Color.score_color(points, maxpoints)
        widths = (Solution.cmd_maxlen, 8, 9, 6, 6)
        colnames = [
            self.run_cmd,
            self.statistics.maxtime,
            self.statistics.sumtime,
            points,
            self.statistics.result,
        ]

        return table_row(color, colnames, widths, [-1, 1, 1, 1, 0])

    def record(self, ifile: str, status: Status, times: Sequence[float]) -> None:
        input = ifile.rsplit("/", 1)[1].rsplit(".", 1)[0]
        batch = input if input.endswith("sample") else input.rsplit(".", 1)[0]
        batchresults = self.statistics.batchresults
        batchresults[batch] = self.updated_status(
            batchresults.get(batch, Status.ok), status
        )
        self.statistics.times[batch].append(tuple(times))
        self.statistics.sumtime += times[0]

        old_status = self.statistics.result
        new_status = self.updated_status(old_status, status)
        if old_status == new_status == status and status.warntle is not None:
            new_status = new_status.set_warntle(
                status.warntle if status.warntle else old_status.warntle
            )
        self.statistics.result = new_status

    def get_timelimit(self, timelimits: dict[Langs.Lang | str, float]) -> float:
        if self.ext in timelimits:
            return timelimits[self.ext]
        if self.lang in timelimits:
            return timelimits[self.lang]
        return timelimits[Langs.Lang.unknown]

    def get_exec_cmd(
        self, ifile: str, tfile: str, timelimit: float = 0.0, memorylimit: float = 0.0
    ) -> Tuple[str, str]:
        timefile = ".temptime-%s-%s-%s.tmp" % (
            to_base_alnum(self.name),
            to_base_alnum(ifile),
            os.getpid(),
        )

        str_memorylimit = int(memorylimit * 1024) if memorylimit else "unlimited"
        ulimit_cmd = "ulimit -m %s; ulimit -s %s" % (str_memorylimit, str_memorylimit)
        timelimit_cmd = "timeout %s" % timelimit if timelimit else ""
        time_cmd = '/usr/bin/time -f "%s" -a -o %s -q' % ("%e %U %S", timefile)
        date_cmd = "date +%%s%%N >>%s" % timefile
        prog_cmd = "%s %s <%s >%s" % (self.run_cmd, self.run_args(ifile), ifile, tfile)
        cmd = "%s; %s; %s %s %s; rc=$?; %s; exit $rc" % (
            ulimit_cmd,
            date_cmd,
            time_cmd,
            timelimit_cmd,
            prog_cmd,
            date_cmd,
        )
        return timefile, cmd

    def run_args(self, ifile: str) -> str:
        return ""

    def run(
        self, ifile: str, ofile: str, tfile: str, checker: Checker, args: ArgsTester
    ) -> None:
        batch = os.path.basename(ifile).split(".")[0]
        if args.fskip and batch in self.statistics.failedbatches:
            return

        isvalidator = isinstance(self, Validator)
        if not self.ready:
            error("%s not prepared for execution" % self.name)
        so = subprocess.PIPE if self.quiet else None
        se = subprocess.PIPE if self.quiet else None

        # run solution
        run_times = [-1] * 4
        timelimit = self.get_timelimit(Config.timelimits)
        memorylimit = float(args.memorylimit)
        timefile, cmd = self.get_exec_cmd(ifile, tfile, timelimit, memorylimit)
        try:
            result = subprocess.call(cmd, stdout=so, stderr=se, shell=True)
            if result == 0:
                status = Status.ok
            elif result == 124:
                status = Status.tle
            elif result > 0:
                status = Status.exc
            else:
                status = Status.err
            try:
                with open(timefile, "r") as tf:
                    ptime_start, *run_times, ptime_end = map(float, tf.read().split())
                    run_times = [int((ptime_end - ptime_start) / 1e6)] + run_times
            except:
                run_times = [-1] * 4
                if status == Status.ok:
                    status = Status.exc
            if status == Status.ok and not isvalidator:
                if checker.check(ifile, ofile, tfile):
                    status = Status.wa
        except Exception as e:
            result = -1
            status = Status.err
            warning(str(e))
        finally:
            if os.path.exists(timefile):
                os.remove(timefile)

        if status is not Status.ok:
            self.statistics.failedbatches.add(batch)
        if isvalidator and (status in (Status.ok, Status.wa)):
            status = Status.valid

        warntle = self.get_timelimit(Config.warn_timelimits) * 1000
        status = status.set_warntle(
            not isvalidator and warntle != 0 and run_times[0] >= warntle
        )

        # construct summary
        self.record(ifile, status, run_times)
        run_cmd = ("{:<" + str(Solution.cmd_maxlen) + "s}").format(self.run_cmd)
        time = "{:6d}ms [{:6.2f}={:6.2f}+{:6.2f}]".format(*run_times)

        if args.inside_oneline:
            input = ("{:" + str(args.inside_inputmaxlen) + "s}").format(
                (ifile.rsplit("/", 1)[1])
            )
            summary = "%s < %s %s" % (run_cmd, input, time)
        else:
            summary = "    %s  %s" % (run_cmd, time)

        print(Color.colorize(status, summary), status.colored())

        if status == Status.err:
            error("Internal error. Testing will not continue", doquit=True)


class Validator(Solution):
    @staticmethod
    def filename_befits(filename: str) -> bool:
        return to_base_alnum(filename).startswith("val")

    def compare_mask(self) -> Tuple[int, int, str]:
        return (-2, 0, self.name)

    def updated_status(self, original: Status, new: Status) -> Status:
        if original == Status.valid:
            return new
        if new == Status.valid:
            return original
        if original == Status.err or new == Status.err:
            return Status.err
        return original

    def get_statistics(self) -> str:
        for key in self.statistics.batchresults:
            self.statistics.maxtime = max(
                self.statistics.maxtime,
                max(map(lambda ts: ts[0], self.statistics.times[key])),
            )
        color = Color.score_color(self.statistics.result == Status.valid, 1)
        widths = (Solution.cmd_maxlen, 8, 9, 6, 6)
        colnames = [
            self.run_cmd,
            self.statistics.maxtime,
            self.statistics.sumtime,
            "",
            self.statistics.result,
        ]

        return table_row(color, colnames, widths, [-1, 1, 1, 1, 0])

    def run_args(self, ifile: str) -> str:
        return " ".join(ifile.split("/")[-1].split(".")) + " "

    def __init__(self, name: str, args: Args):
        super().__init__(name, args)
        self.statistics.result = Status.valid


class Checker(Program):
    @staticmethod
    def filename_befits(filename: str) -> str | None:
        filename = to_base_alnum(filename)
        prefixes = ["diff", "check", "chito", "test"]
        for prefix in prefixes:
            if filename.startswith(prefix):
                return prefix
        return None

    def compare_mask(self) -> Tuple[int, int, str]:
        return (-3, 0, self.name)

    def __init__(self, name: str, args: Args):
        super().__init__(name, args)
        if name == "diff":
            self.run_cmd = "diff"
            self.compilecmd = None
            self.forceexecute = True

    def diff_cmd(self, ifile: str, ofile: str, tfile: str) -> str | None:
        diff_map = {
            "diff": " %s %s > /dev/null" % (ofile, tfile),
            "check": " %s %s %s > /dev/null" % (ifile, ofile, tfile),
            "chito": " %s %s %s > /dev/null" % (ifile, tfile, ofile),
            "test": " %s %s %s %s %s" % ("./", "./", ifile, ofile, tfile),
        }
        prefix = self.filename_befits(self.name)
        if prefix:
            return self.run_cmd + diff_map[prefix]
        return None

    def check(self, ifile: str, ofile: str, tfile: str) -> int:
        se = subprocess.PIPE if self.quiet else None
        cmd = self.diff_cmd(ifile, ofile, tfile)
        if cmd is None:
            error("Unsupported checker %s" % self.name)
            return -1
        result = subprocess.call(cmd, shell=True, stderr=se)
        if not result in (0, 1):
            warning("Checker exited with status %s" % result)
        return result


class Generator(Program):
    def compare_mask(self) -> Tuple[int, int, str]:
        return (-4, 0, self.name)

    def generate(self, ifile: str, text: str) -> Status:
        cmd = "%s > %s" % (self.run_cmd, ifile)
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
        p.communicate(str.encode(text))
        return Status.exc if p.returncode else Status.ok


"""
# compile the wrapper if turned on
wrapper_binary = None
if args.wrapper != False:
    path = args.wrapper or '$WRAPPER'
    if os.uname()[-1] == 'x86_64':
        wrapper_source='%s/wrapper-mj-amd64.c' % path
    else:
        wrapper_source='%s/wrapper-mj-x86.c' % path
    wrapper_binary='%s/wrapper' % path
    if os.system('gcc -O2 -o %s %s' % (wrapper_binary, wrapper_source)):
        error('Wrapper compile failed.')
        quit(1)
"""
