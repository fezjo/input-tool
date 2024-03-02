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
    from input_tool.common.programs.checker import Checker
    from input_tool.input_tester import (
        create_programs_from_files,
        get_relevant_prog_files_deeper,
        prepare_programs,
    )

    files = get_relevant_prog_files_deeper(args.programs)
    solutions, checker_files = create_programs_from_files(files, True)
    programs = [Checker(checker_file, False) for checker_file in checker_files]
    programs += solutions

    prepare_programs(programs, max(4, args.threads))


def run_colortest(args: itool_parser.specs.ArgsGeneric):
    from input_tool.common.messages import color_test

    color_test()


def run_checkupdates(args: itool_parser.specs.ArgsGeneric):
    from input_tool.common.check_updates import main

    main()


def main():
    unified_parser = itool_parser.UnifiedParser()
    subcommand, args = unified_parser.parse()
    subcommand_funcs = {
        "sample": run_sample,
        "generate": run_generator,
        "test": run_tester,
        "compile": run_compile,
        "colortest": run_colortest,
        "checkupdates": run_checkupdates,
    }
    subcommand_funcs[subcommand](args)


if __name__ == "__main__":
    main()
