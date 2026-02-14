# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from input_tool.common.commands import Config, Langs, is_file_newer, to_base_alnum
from input_tool.common.messages import Logger, default_logger, fatal


class Program:
    def __init__(self, name: str):
        self.name = name

        self.quiet: bool = Config.quiet
        self.can_compile: bool = Config.compile
        self.force_execute: bool = Config.execute
        self.ready = False

        # `extensions` is either easily extracted from `name`
        # or if it's missing, we try to guess it.
        self.extension: Optional[str] = None
        # it's either `name` or we try to find it by adding extensions
        self.source_path: Optional[Path] = None
        # the executable can be compiled into a different directory
        self.executable_path: Optional[Path] = None

        self.lang: Langs.Lang = Langs.Lang.unknown
        self.compile_cmd: Optional[str] = None
        self.run_cmd: Optional[str] = None
        self.files_to_clear: list[Path] = []

        # compute run_cmd, compile_cmd and files_to_clear
        self._transform()

    @staticmethod
    def filename_befits(filename: str) -> bool:
        raise NotImplementedError

    def compare_mask(self) -> tuple[int, int, str]:
        return (0, 0, self.name)

    def _transform(self) -> None:
        self.run_cmd = self.name  # default if no transformation applies

        # if it is final command, dont do anything
        if self.force_execute:
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
            if not valid:
                # could not guess the extension, so we don't know how to compile or run it
                return
            self.source_path = Path(self.name + "." + valid[0])
            if os.path.exists(self.name):
                valid.append("<noextension>")
            if len(valid) > 1:
                default_logger.warning(
                    f"Warning: multiple possible sources for {self.name}, "
                    f"using first {valid}"
                )
        else:
            self.source_path = Path(self.name)

        self.extension = self.source_path.suffix.lstrip(".").lower()
        self.lang = Langs.from_ext(self.extension)
        if self.lang is Langs.Lang.unknown:
            return

        def get_tmpdir(base: Path):
            path = base / ".dir-{}-{}.tmp".format(to_base_alnum(self.name), os.getpid())
            path.mkdir(exist_ok=True)
            self.files_to_clear.append(path)
            return path

        def setup_compile_by_make(options: list[str]) -> None:
            """
            self.run_cmd and Config.progdir can be:
            /dir/exe, ~/dir/exe, ../dir/exe, ./dir/exe, dir/exe, exe,
            and needs to work with includes.
            """
            assert self.source_path is not None
            exe = self.source_path.with_suffix("")
            if not Config.progdir:
                self.compile_cmd = f"make {options} {exe}"
                self.executable_path = Path(exe)
            else:
                path, exe = exe.parent, exe.name
                path = min(
                    os.path.relpath(path, Config.progdir),
                    os.path.abspath(path),
                    key=len,
                )
                option_str = " ".join(filter(bool, options))
                self.compile_cmd = (
                    f'cd {Config.progdir}; make VPATH="{path}" {option_str} {exe}'
                )
                self.executable_path = Path(os.path.join(Config.progdir, exe))

        def setup_with_compiled_executable() -> None:
            assert self.executable_path is not None
            self.files_to_clear.append(self.executable_path)
            self.run_cmd = str(self.executable_path)

        if self.lang in Langs.lang_compiled:
            progdir = Path(Config.progdir or ".")
            basename = self.source_path.stem
            if not self.can_compile:
                self.run_cmd = basename
            elif self.lang is Langs.Lang.c:
                compiler = Config.os_config.cmd_cpp_compiler
                option_list = [
                    f'CC="{compiler}"' if compiler else "",
                    'CFLAGS="-O2 -g -std=c17 $CFLAGS"',
                ]
                setup_compile_by_make(option_list)
                setup_with_compiled_executable()
            elif self.lang is Langs.Lang.cpp:
                compiler = Config.os_config.cmd_cpp_compiler
                option_list = [
                    f'CXX="{compiler}"' if compiler else "",
                    'CXXFLAGS="-O2 -g -std=c++20 $CXXFLAGS"',
                ]
                setup_compile_by_make(option_list)
                setup_with_compiled_executable()
            elif self.lang is Langs.Lang.haskell:
                outdir = get_tmpdir(progdir)
                self.executable_path = Path(progdir) / basename
                options = (
                    "-O2 -rtsopts --make"
                    f" -tmpdir {outdir} -outputdir {outdir} -o {self.executable_path}"
                )
                self.compile_cmd = (
                    f"{Config.os_config.cmd_haskell} {options} {self.source_path}"
                )
                setup_with_compiled_executable()
            elif self.lang is Langs.Lang.java:
                outdir = get_tmpdir(progdir)
                self.compile_cmd = f"javac {self.source_path} -d {outdir}"
                self.run_cmd = f"java -Xss256m -cp {outdir} {basename}"
            elif self.lang is Langs.Lang.pascal:
                outdir = get_tmpdir(progdir)
                options = f"-O1 -Sg -FU{outdir} -o{outdir}/{basename}"
                self.compile_cmd = (
                    f"fpc {options} {self.source_path}"
                    f" && mv {outdir}/{basename} {progdir}/{basename}"
                )  # TODO hacky and not cross platform
                self.executable_path = Path(progdir) / basename
                setup_with_compiled_executable()
            elif self.lang is Langs.Lang.rust:
                options = f"-C opt-level=2 --out-dir {progdir}"
                self.compile_cmd = f"rustc {options} {self.source_path}"
                self.executable_path = Path(progdir) / basename
                setup_with_compiled_executable()
            else:
                assert False, "unreachable"

            # user asked us to run:
            need_compilation = self.executable_path is None or (
                # source/executable, but the associated executable doesn't exist
                not os.path.exists(self.executable_path)
                # a source file and it is newer than the executable
                or (
                    self.name == str(self.source_path)
                    and is_file_newer(str(self.source_path), str(self.executable_path))
                )
                # so if user specified an executable (not source, but guessed something),
                # we will not recompile even if it is comparatively stale
            )
            if not need_compilation:
                self.compile_cmd = None
                default_logger.infob(f"Executable {self.run_cmd} is up to date.")

        elif self.lang in Langs.lang_script:
            if os.access(self.source_path, os.X_OK):
                # even if they are scripts, we prefer to run them if they are executable
                # because they might have shebangs or something, and we want to respect that
                self.run_cmd = str(self.source_path)
            elif self.lang is Langs.Lang.python:
                self.run_cmd = f"{Config.os_config.cmd_python} {self.source_path}"
            elif self.lang is Langs.Lang.javascript:
                self.run_cmd = f"{Config.os_config.cmd_node} {self.source_path}"
            else:
                assert False, "unreachable"

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
        if self.compile_cmd is not None:
            logger.infob(f"Compiling: {self.compile_cmd}")
            fresh_compiled = True
            result = subprocess.run(
                self.compile_cmd,
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
            not self.force_execute
            and os.access(self.run_cmd, os.X_OK)
            and self.run_cmd[0].isalnum()
        ):
            self.run_cmd = "./" + self.run_cmd

        # MacOS is stupid or whatever and it will virus check or sign the binary or something
        # so we need to run it once and wait for it to do whatever it does (1s should be enough?)
        if fresh_compiled and Config.os_config.stupid_macos and not self.force_execute:
            logger.infob(f"Prewarming binary: {self.run_cmd}")
            cmd = [Config.os_config.cmd_timeout, "0.001", self.run_cmd]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)

        self.ready = True

    def clear_files(self) -> None:
        for f in self.files_to_clear:
            if os.path.exists(f):
                if os.path.isdir(f):
                    shutil.rmtree(f)
                else:
                    os.remove(f)
            else:
                default_logger.warning(f"Not found {f}")
