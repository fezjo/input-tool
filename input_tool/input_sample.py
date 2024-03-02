#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
# Script that creates sample inputs from task statements or vice versa
import os
import sys
from typing import Optional, Sequence

from input_tool.common.messages import (
    Color,
    default_logger,
    fatal,
    info,
    infob,
    warning,
)
from input_tool.common.parser.parser import Parser
from input_tool.common.parser.specifications import (
    ArgsSample,
    description_sample,
    options_sample,
)
from input_tool.common.recipes import Input, Sample, prepare_cumber

# TODO Can be used in opposite direction.
# TODO smart -- detect prefix and multi.


def parse_args() -> ArgsSample:
    parser = Parser(description_sample, options_sample)
    return parser.parse(ArgsSample)


def read_recipe(path: Optional[str]) -> list[str]:
    if path:
        if not os.path.exists(path):
            fatal(f"Path '{path}' does not exist.")
        elif os.path.isdir(path):
            consider = [f for f in os.listdir(path) if f.lower() == "zadanie.md"]
            if len(consider) == 0:
                fatal(f"Path '{path}' does not contain `zadanie.md`.")
            elif len(consider) > 1:
                fatal(
                    f"Path '{path}' contains more than one `zadanie.md`."
                    f"Specify which one to use {consider}."
                )
            path = os.path.join(path, consider[0])
        return open(path, "r").readlines()
    return sys.stdin.readlines()


TIPS: list[str] = []

warning_messages = {
    "noend": "In {} some line does not end with \\n",
    "empty": "{} is empty",
    "emptyline": "{} is just an empty line",
    "ws-start": "In {} some line starts with a whitespace",
    "ws-end": "In {} some line ends with a whitespace",
    "bl-start": "{} starts with blank line",
    "bl-end": "{} ends with blank line",
}


def check_line(line: str) -> None:
    if line != "\n" and line.lstrip() != line:
        TIPS.append("ws-start")
    if line[-1] != "\n":
        TIPS.append("noend")
    else:
        if line.rstrip() != line[:-1].rstrip():
            TIPS.append("ws-end")


def check_text(text: str) -> None:
    if text == "":
        TIPS.append("empty")
    elif text == "\n":
        TIPS.append("emptyline")
    else:
        if text[0] == "\n":
            TIPS.append("bl-start")
        if text[-1] == "\n" and text[-2] == "\n":
            TIPS.append("bl-end")


def process_lines(lines: Sequence[str]) -> tuple[list[str], list[str]]:
    samples_in: list[str] = []
    samples_out: list[str] = []
    active: list[str] | None = None
    active_lines = ""
    for line in lines:
        if line.strip() == "```vstup":
            active = samples_in
            active_lines = ""
            continue
        if line.strip() == "```vystup":
            active = samples_out
            active_lines = ""
            continue
        if line.strip() == "```":
            if active is not None:
                active.append(active_lines)
            active = None
        elif active is not None:
            check_line(line)
            active_lines += line
    return samples_in, samples_out


def get_samples(
    samples_in: Sequence[str], samples_out: Sequence[str], args: ArgsSample
) -> list[Sample]:
    samples: list[Sample] = []
    for i in range(len(samples_in)):
        samples.append(
            Sample(samples_in[i], args.indir, args.batchname, i, args.inext),
        )
        samples.append(
            Sample(samples_out[i], args.outdir, args.batchname, i, args.outext),
        )
    return samples


def prepare_samples(samples: Sequence[Sample]) -> None:
    for sample in samples:
        check_text(sample.text)
        sample.compile()


def print_tips() -> None:
    tips = sorted(list(set(TIPS)))
    for w in tips:
        message = warning_messages[w].format("some input/output")
        message = message[0].upper() + message[1:]
        warning(message)


def prepare_dirs(dirs: Sequence[str]) -> None:
    for d in dirs:
        if not os.path.exists(d):
            infob(f"Creating directory '{d}'")
            os.makedirs(d)


def run(args: ArgsSample) -> None:
    Color.setup(args.colorful)
    prepare_cumber(args.batchname)

    lines = read_recipe(args.task)
    if args.multi:
        Input.maxid = 1

    samples_in, samples_out = process_lines(lines)
    if len(samples_in) != len(samples_out):
        fatal("Number of inputs and outputs must be the same.")
    if len(samples_in) == 0:
        warning("No inputs found in task statements.")

    samples = get_samples(samples_in, samples_out, args)
    prepare_samples(samples)
    print_tips()

    prepare_dirs((args.indir, args.outdir))
    for sample in samples:
        sample.save()

    info(str(default_logger.statistics))


def main():
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
