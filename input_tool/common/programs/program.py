from __future__ import annotations
import os
import shutil
import subprocess
from typing import Optional

from input_tool.common.commands import to_base_alnum, Config, Langs, is_file_newer
from input_tool.common.messages import default_logger, Logger


class Program:
    def __init__(self, name: str):
        self.name = name
        self.quiet: bool = Config.quiet
        self.cancompile: bool = Config.compile
        self.forceexecute: bool = Config.execute
        self.ready = False

        # compute run_cmd, compilecmd and filestoclear
        self._transform()

    def compare_mask(self) -> tuple[int, int, str]:
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
                default_logger.warning(
                    f"Warning: multiple possible sources for {self.name}, using first {valid}"
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

        def setup_compile_by_make(options: str) -> None:
            """
            self.run_cmd and Config.progdir can be:
            /dir/exe, ~/dir/exe, ../dir/exe, ./dir/exe, dir/exe, exe
            """
            path, exe = os.path.split(self.run_cmd)
            path = path if path else "."
            path = min(
                os.path.relpath(path, Config.progdir), os.path.abspath(path), key=len
            )
            self.compilecmd = (
                f"cd {Config.progdir}; make VPATH='{path}' {options} {exe}"
            )
            self.run_cmd = f"{Config.progdir}/{exe}"
            self.filestoclear.append(self.run_cmd)

        if docompile:
            if self.lang is Langs.Lang.c:
                setup_compile_by_make('CFLAGS="-O2 -std=c17 $CFLAGS"')
            elif self.lang is Langs.Lang.cpp:
                setup_compile_by_make('CXXFLAGS="-O2 -std=c++20 $CXXFLAGS"')
            elif self.lang is Langs.Lang.pascal:
                setup_compile_by_make('PFLAGS="-O2 $FFLAGS"')
            elif self.lang is Langs.Lang.java:
                class_dir = "{}/.classdir-{}-{}.tmp".format(
                    Config.progdir, to_base_alnum(self.name), os.getpid()
                )
                os.mkdir(class_dir)
                self.compilecmd = f"javac {self.source} -d {class_dir}"
                self.filestoclear.append(class_dir)
                self.run_cmd = f"-cp {class_dir} {self.run_cmd}"
            elif self.lang is Langs.Lang.rust:
                options = f"-C opt-level=2 --out-dir {Config.progdir}"
                self.compilecmd = f"rustc {options} {self.run_cmd}.rs"
                self.run_cmd = f"{Config.progdir}/{self.run_cmd}"
                self.filestoclear.append(self.run_cmd)

        if not os.access(self.run_cmd, os.X_OK):
            if self.lang is Langs.Lang.python:
                self.run_cmd = f"{Config.pythoncmd} {self.source}"
            if self.lang is Langs.Lang.java:
                self.run_cmd = "java -Xss256m " + self.run_cmd

    def prepare(self, logger: Optional[Logger] = None) -> None:
        logger = default_logger if logger is None else logger
        if self.compilecmd != None:
            logger.infob(f"Compiling: {self.compilecmd}")
            result = subprocess.run(
                self.compilecmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if not self.quiet:
                logger.plain(result.stdout.decode("utf-8"))
            if result.returncode:
                logger.error("Compilation failed.")

        assert self.run_cmd
        if (
            not self.forceexecute
            and os.access(self.run_cmd, os.X_OK)
            and self.run_cmd[0].isalnum()
        ):
            self.run_cmd = "./" + self.run_cmd

        self.ready = True

    def clear_files(self) -> None:
        for f in self.filestoclear:
            if os.path.exists(f):
                if os.path.isdir(f):
                    shutil.rmtree(f)
                else:
                    os.remove(f)
            else:
                default_logger.warning(f"Not found {f}")
