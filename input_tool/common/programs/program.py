# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import Optional

from input_tool.common.commands import Config, Langs, is_file_newer, to_base_alnum
from input_tool.common.messages import Logger, default_logger, fatal


class Program:
    def __init__(self, name: str):
        self.name = name
        self.quiet: bool = Config.quiet
        self.cancompile: bool = Config.compile
        self.forceexecute: bool = Config.execute
        self.ready = False

        # compute run_cmd, compilecmd and filestoclear
        self._transform()

    @staticmethod
    def filename_befits(filename: str) -> bool:
        raise NotImplementedError

    def compare_mask(self) -> tuple[int, int, str]:
        return (0, 0, self.name)

    def _transform(self) -> None:
        self.compilecmd = None
        self.source = None
        self.ext = None
        self.run_cmd = self.name
        self.filestoclear: list[str] = []
        self.lang: Langs.Lang = Langs.Lang.unknown

        # if it is final command, dont do anything
        if self.forceexecute:
            return
        if len(self.name.split()) > 1:
            if os.path.exists(self.name):
                fatal(f"Error: whitespace in filenames not supported [{self.name}]")
            return

        # compute source, binary and extension
        # TODO: base self.name can have multiple sources
        if "." not in self.name:
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
                    f"Warning: multiple possible sources for {self.name}, "
                    f"using first {valid}"
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

        def setup_compile_by_make(options: list[str]) -> None:
            """
            self.run_cmd and Config.progdir can be:
            /dir/exe, ~/dir/exe, ../dir/exe, ./dir/exe, dir/exe, exe,
            and needs to work with includes.
            """
            if not Config.progdir:
                self.compilecmd = f"make {options} {self.run_cmd}"
            else:
                path, exe = os.path.split(self.run_cmd)
                path = path if path else "."
                path = min(
                    os.path.relpath(path, Config.progdir),
                    os.path.abspath(path),
                    key=len,
                )
                option_str = " ".join(filter(bool, options))
                self.compilecmd = (
                    f'cd {Config.progdir}; make VPATH="{path}" {option_str} {exe}'
                )
                self.run_cmd = os.path.join(Config.progdir, exe)
            self.filestoclear.append(self.run_cmd)

        if docompile:
            progdir = Config.progdir or os.path.curdir
            if self.lang is Langs.Lang.c:
                compiler = Config.os_config.cmd_cpp_compiler
                option_list = [
                    f'CC="{compiler}"' if compiler else "",
                    'CFLAGS="-O2 -g -std=c17 $CFLAGS"',
                ]
                setup_compile_by_make(option_list)
            elif self.lang is Langs.Lang.cpp:
                compiler = Config.os_config.cmd_cpp_compiler
                option_list = [
                    f'CXX="{compiler}"' if compiler else "",
                    'CXXFLAGS="-O2 -g -std=c++20 $CXXFLAGS"',
                ]
                setup_compile_by_make(option_list)
            elif self.lang is Langs.Lang.pascal:
                self.run_cmd = os.path.join(progdir, self.run_cmd)
                options = f"-O1 -Sg -o{self.run_cmd}"
                self.compilecmd = f"fpc {options} {self.source}"
                self.filestoclear.append(self.run_cmd)
            elif self.lang is Langs.Lang.java:
                outdir = os.path.join(
                    progdir,
                    ".dir-{}-{}.tmp".format(to_base_alnum(self.name), os.getpid()),
                )
                os.mkdir(outdir)
                self.compilecmd = f"javac {self.source} -d {outdir}"
                self.filestoclear.append(outdir)
                self.run_cmd = f"java -Xss256m -cp {outdir} {self.run_cmd}"
            elif self.lang is Langs.Lang.rust:
                options = f"-C opt-level=2 --out-dir {progdir}"
                self.compilecmd = f"rustc {options} {self.source}"
                self.run_cmd = os.path.join(progdir, self.run_cmd)
                self.filestoclear.append(self.run_cmd)

        if not os.access(self.run_cmd, os.X_OK):
            if self.lang is Langs.Lang.python:
                self.run_cmd = f"{Config.os_config.cmd_python} {self.source}"

    @staticmethod
    def get_possible_locations_of_executable(run_cmd: str, source: str) -> list[str]:
        source_dir, source_basename = os.path.split(source)
        source_name, _source_ext = os.path.splitext(source_basename)
        _run_cmd_dir, run_cmd_basename = os.path.split(run_cmd)
        possibilities = [
            run_cmd,
            os.path.join(source_dir, run_cmd_basename),
            os.path.join(source_dir, source_name),
            os.path.join(source_dir, source_basename),
            run_cmd_basename,
            source_name,
            source_basename,
        ]
        # keep unique in original order
        return list(dict.fromkeys(possibilities))

    @staticmethod
    def try_possible_locations_of_executable(possibilities: list[str]) -> Optional[str]:
        for cmd in possibilities:
            if os.access(cmd, os.X_OK):
                return cmd
        return None

    def prepare(self, logger: Optional[Logger] = None) -> None:
        assert self.run_cmd is not None
        logger = default_logger if logger is None else logger
        fresh_compiled = False
        if self.compilecmd is not None:
            logger.infob(f"Compiling: {self.compilecmd}")
            fresh_compiled = True
            result = subprocess.run(
                self.compilecmd,
                shell=True,
                stdout=subprocess.PIPE,
                # TODO if stderr=subprocess.STDOUT, it would stream during compilation
                stderr=subprocess.PIPE,
            )
            stderr = result.stderr.decode("utf-8")
            if stderr:
                logger.infod(stderr)
                logger.statistics.compilation_warnings += stderr.count("warning:")
            if not self.quiet:
                stdout = result.stdout.decode("utf-8")
                if "up to date" in stdout:  # TODO: find more robust way
                    fresh_compiled = False
                logger.plain(stdout)
            if result.returncode:
                logger.fatal("Compilation failed.")

            if self.lang is not Langs.Lang.java:
                possible_cmds = self.get_possible_locations_of_executable(
                    self.run_cmd, self.name
                )
                found_cmd = self.try_possible_locations_of_executable(possible_cmds)
                if found_cmd is None:
                    logger.fatal(f"Error: No executable found for {self.name}")
                elif found_cmd != self.run_cmd:
                    logger.warning(
                        f"Warning: {self.run_cmd} not found, using {found_cmd} instead."
                    )
                    self.run_cmd = found_cmd

        if (
            not self.forceexecute
            and os.access(self.run_cmd, os.X_OK)
            and self.run_cmd[0].isalnum()
        ):
            self.run_cmd = "./" + self.run_cmd

        # MacOS is stupid or whatever and it will virus check or sign the binary or something
        # so we need to run it once and wait for it to do whatever it does (1s should be enough?)
        if fresh_compiled and Config.os_config.stupid_macos and not self.forceexecute:
            logger.infob(f"Prewarming binary: {self.run_cmd}")
            cmd = [Config.os_config.cmd_timeout, "0.001", self.run_cmd]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)

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
