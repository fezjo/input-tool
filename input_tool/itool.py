#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# © 2024 fezjo
# Unified script for input-tool
import input_tool.common.parser.parser as itool_parser


def run_sample(args: itool_parser.specs.ArgsSample):
    from input_tool.input_sample import run

    run(args)


def run_generator(args: itool_parser.specs.ArgsGenerator):
    from input_tool.input_generator import run

    run(args)


def run_tester(args: itool_parser.specs.ArgsTester):
    from input_tool.input_tester import run

    run(args)


def run_compile(args: itool_parser.specs.ArgsCompile):
    from input_tool.common.commands import Config
    from input_tool.common.programs.checker import Checker
    from input_tool.common.tools_common import setup_config
    from input_tool.input_tester import (
        create_programs_from_files,
        get_relevant_prog_files_deeper,
        prepare_programs,
    )

    setup_config(args, ("progdir", "quiet", "colorful"))
    Config.compile = True
    Config.execute = False

    files = get_relevant_prog_files_deeper(args.programs)
    solutions, checker_files = create_programs_from_files(files, True)
    programs = solutions + [Checker(file, False) for file in checker_files]

    prepare_programs(programs, max(4, args.threads))


def run_autogenerate(args: itool_parser.specs.ArgsAutogenerate):
    from input_tool.input_generator import run as run_generator
    from input_tool.input_tester import run as run_tester

    args_generator = itool_parser.specs.convert_args(
        args, itool_parser.specs.ArgsGenerator
    )
    args_tester = itool_parser.specs.convert_args(
        args,
        itool_parser.specs.ArgsTester,
        sort=True,
        dupprog=False,
        bestonly=True,
        reset=True,
        rustime=False,
        timelimit="0",
        warntimelimit="0",
        memorylimit=0,
        diffcmd="diff",
        showdiff=False,
        fail_skip=False,
        ioram=False,
    )
    run_generator(args_generator)
    run_tester(args_tester)


def run_colortest(args: itool_parser.specs.ArgsGeneric):
    from input_tool.common.messages import color_test

    color_test()


def run_checkupdates(args: itool_parser.specs.ArgsGeneric):
    from input_tool.common.check_updates import main

    main()


def main():
    # specification:  description_X, short_description_X, options_X, ArgsX, Args, ArgsT
    # parser:         subcommand, alias_mapping, mapping
    # itool:          subcommand_funcs

    unified_parser = itool_parser.UnifiedParser()
    subcommand, args = unified_parser.parse()
    subcommand_funcs = {
        "sample": run_sample,
        "generate": run_generator,
        "test": run_tester,
        "compile": run_compile,
        "autogenerate": run_autogenerate,
        "colortest": run_colortest,
        "checkupdates": run_checkupdates,
    }
    subcommand_funcs[subcommand](args)


if __name__ == "__main__":
    main()
