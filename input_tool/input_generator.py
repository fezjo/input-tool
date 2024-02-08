#!/usr/bin/env python3
# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
# Script that helps generating inputs for contests
import atexit
import os
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional

from input_tool.common.check_updates import check_for_updates
from input_tool.common.messages import (
    Color,
    Status,
    default_logger,
    error,
    fatal,
    info,
    infob,
)
from input_tool.common.parser import ArgsGenerator, Parser
from input_tool.common.programs.generator import Generator
from input_tool.common.recipes import Input, Recipe
from input_tool.common.tools_common import (
    check_data_folder_size,
    cleanup,
    prepare_programs,
    setup_config,
)

description = """
Input generator.
Generate inputs based on input description file. Each line is provided as input to
generator. Empty lines separate batches.
"""
options = [
    "indir",
    "progdir",
    "inext",
    "compile",
    "execute",
    "gencmd",
    "pythoncmd_gen",
    "threads_gen",
    "colorful",
    "quiet",
    "clearinput",
    "noclearbin",
    "clearbin",
    "description",
]


def parse_args() -> ArgsGenerator:
    parser = Parser(description, options)
    return parser.parse(ArgsGenerator)


def find_idf(directory: str) -> str:
    idfs: list[str] = []
    for de in os.scandir(directory):
        if de.is_file() and de.name.startswith("idf"):
            idfs.append(de.path)
    if len(idfs) != 1:
        fatal(
            f"Found {len(idfs)} idf files {idfs} in directory '{directory}'.\n"
            f"Please specify idf file manually."
        )
    return idfs[0]


def get_recipe(file: Optional[str]) -> Recipe:
    if file is not None:
        if os.path.isdir(file):
            file = find_idf(file)
        with open(file, "r") as f:
            text = f.readlines()
    else:
        text = sys.stdin.readlines()
    return Recipe(text)


def setup_indir(indir: str, inext: str, clear_input: bool) -> None:
    if not os.path.exists(indir):
        infob(f"Creating directory '{indir}'")
        os.makedirs(indir)

    filestoclear = os.listdir(indir)
    if filestoclear and clear_input:
        infob(f"Cleaning directory '{indir}:'")
        # delete only following files
        exttodel = ["in", "out", "temp", inext]
        for file in filestoclear:
            if file.endswith(inext) and "sample" in file:
                info(f"  ommiting file '{file}'")
            elif file.rsplit(".", 1)[-1] not in exttodel:
                info(f"  not deleting file '{file}'")
            else:
                os.remove(f"{indir}/{file}")


def get_ifile(x: Input, args: ArgsGenerator, path: bool = False) -> str:
    return x.get_name(path=args.indir + "/" if path else "", ext=args.inext)


def print_message_for_input(
    leftw: int, status: Status, input: Input, prev: Optional[Input], args: ArgsGenerator
) -> None:
    short = ("{:>" + str(leftw) + "s}").format(get_ifile(input, args))

    if prev and prev.batch != input.batch:
        print(" " * (leftw + 4) + ".")

    msg = "  {}  <  {}".format(short, input.get_info_text(len(short) + 4))
    if status != Status.ok:
        msg = msg.ljust(50) + " Generator encountered an error!"
        error(Color.status_colorize(status, msg))
    else:
        info(Color.status_colorize(status, msg))


def generate_all(
    recipe: Recipe,
    programs: dict[str, Generator],
    default_gencmd: str,
    args: ArgsGenerator,
) -> None:
    def submit_input(executor: ThreadPoolExecutor, input: Input) -> Future:
        return executor.submit(
            programs[input.generator or default_gencmd].generate,
            get_ifile(input, args, True),
            input.get_generation_text(),
        )

    infob("Generating:")
    leftw = max([len(get_ifile(i, args)) for i in recipe.inputs])
    prev = None
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [(submit_input(executor, input), input) for input in recipe.inputs]
        for future, input in futures:
            print_message_for_input(leftw, future.result(), input, prev, args)
            prev = input
    infob("Done")


def main() -> None:
    args = parse_args()
    setup_config(args, ("progdir", "quiet", "compile", "execute"))

    recipe = get_recipe(args.description)
    recipe.process()
    recipe.inputs.sort()

    programs = {x: Generator(x) for x in recipe.programs}
    gencmd = args.gencmd
    programs[gencmd] = Generator(gencmd)
    prepare_programs(programs.values(), max(4, args.threads))
    if args.clearbin:
        atexit.register(lambda p=programs: cleanup(tuple(p.values())))

    setup_indir(args.indir, args.inext, args.clearinput)
    generate_all(recipe, programs, gencmd, args)

    check_data_folder_size(args.indir)
    check_for_updates()
    info(str(default_logger.statistics))


if __name__ == "__main__":
    main()
