#!/usr/bin/env python3
# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
# Complex script that can test solutions
import atexit
import itertools
import json
import os
import shutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any, Optional, Sequence

from input_tool.common.commands import Config, Langs, get_statistics_header
from input_tool.common.messages import (
    BufferedLogger,
    ParallelLoggerManager,
    color_test,
    default_logger,
    fatal,
    info,
    infob,
    plain,
    register_quit_signal,
    serialize_for_json,
    warning,
)
from input_tool.common.parser import ArgsTester, Parser
from input_tool.common.programs.checker import Checker
from input_tool.common.programs.program import Program
from input_tool.common.programs.solution import Solution
from input_tool.common.programs.validator import Validator
from input_tool.common.task_history import TASK_HISTORY
from input_tool.common.task_queue import TaskItem, TaskQueue
from input_tool.common.tools_common import (
    check_data_folder_size,
    cleanup,
    prepare_programs,
    register_quit_with_executor,
    setup_config,
)

description = """
Input tester.
Test all given solutions on all inputs.
By default, if outputs don't exits, use the first solution to generate them.
By default, automatically decide, how to compile and run solution.
"""
options = [
    "indir",
    "outdir",
    "progdir",
    "inext",
    "outext",
    "tempext",
    "reset",
    "timelimit",
    "warntimelimit",
    "memorylimit",
    "diffcmd",
    "showdiffoutput",
    "compile",
    "execute",
    "nosort",
    "colorful",
    "colortest",
    "quiet",
    "stats",
    "nostats",
    "json",
    "cleartemp",
    "noclearbin",
    "clearbin",
    "programs",
    "fskip",
    "dupprog",
    "pythoncmd_test",
    "threads_test",
    "rustime",
]

# ----------------- configuration ----------------


def parse_args() -> ArgsTester:
    parser = Parser(description, options)
    return parser.parse(ArgsTester)


def parse_timelimit(timelimit: str) -> Config.Timelimit:
    res: Config.Timelimit = {}
    for p in timelimit.split(","):
        ext, str_t = p.split("=") if "=" in p else ("", p)
        t = timedelta(seconds=float(str_t))
        res[ext] = t
        res[Langs.from_ext(ext)] = t
    return res


def parse_warntimelimit(
    warntimelimit: str, timelimit: Config.Timelimit
) -> Config.Timelimit:
    if warntimelimit == "auto":
        return {k: v / 3 for k, v in timelimit.items()}
    return parse_timelimit(warntimelimit)


# --------------- prepare programs ---------------


def get_relevant_prog_files_in_directory(directory: str) -> list[str]:
    return [
        os.path.normpath(de.path)
        for de in os.scandir(directory)
        if de.is_file()
        and any(cl.filename_befits(de.name) for cl in (Solution, Validator, Checker))
    ]


def get_relevant_prog_files_deeper(candidates: Sequence[str]) -> list[str]:
    return list(
        itertools.chain.from_iterable(
            get_relevant_prog_files_in_directory(p) if os.path.isdir(p) else [p]
            for p in candidates
        )
    )


def create_programs_from_files(
    files: Sequence[str], deduplicate: bool
) -> tuple[list[Solution | Validator], list[str]]:
    solutions: list[Solution | Validator] = []
    checker_files: list[str] = []
    if deduplicate:  # remove duplicate paths keeping order
        files = list(dict.fromkeys(files))
    for p in files:
        if Validator.filename_befits(p):
            solutions.append(Validator(p))
        elif Checker.filename_befits(p):
            checker_files.append(p)
        else:
            solutions.append(Solution(p))
    return solutions, checker_files


def create_checker(
    checker: Optional[str], checker_files: list[str], show_diff_output: bool
) -> Checker:
    if checker is not None:
        checker_files = [checker]
    if not checker_files:
        checker_files.append("diff")
    if len(checker_files) > 1:
        fatal(
            f"More than one checker found {checker_files}.\n"
            "Set explicitly with -d/--diffcmd (e.g. -d diff) "
            "or leave only one checker in the directory."
        )
    return Checker(checker_files[0], show_diff_output)


def deduplicate_solutions(
    solutions: Sequence[Solution | Validator],
) -> list[Solution | Validator]:
    d: dict[str, Program] = {}
    res: list[Solution | Validator] = []
    for s in solutions:
        key = s.run_cmd
        if key in d:
            warning(
                f"Solution {d[key].name} and {s.name} have the same run command. "
                "Keeping only first."
            )
        else:
            d[key] = s
            res.append(s)
    return res


def print_solutions_run_commands(solutions: Sequence[Solution | Validator]) -> None:
    infob("----- Run commands -----")
    for s in solutions:
        infob(f"Program {s.name:{Config.cmd_maxlen}}   is ran as `{s.run_cmd}`")
    infob("------------------------")


# --------------- prepare io files ---------------


def get_inputs(args: ArgsTester) -> list[str]:
    return sorted(filter(lambda x: x.endswith(args.inext), os.listdir(args.indir)))


def get_outputs(inputs: Sequence[str], args: ArgsTester) -> Optional[list[str]]:
    if args.outext != args.tempext and not args.reset:
        outputs = sorted(
            filter(lambda x: x.endswith(args.outext), os.listdir(args.outdir))
        )
        if len(outputs) > 0 and len(outputs) < len(inputs):
            warning("Incomplete output files.")
        return outputs
    else:
        infob("Outputs will be regenerated")
        return None


def temp_clear(args: ArgsTester) -> None:
    tempfiles = sorted(
        filter(lambda x: x.endswith(args.tempext), os.listdir(args.outdir))
    )
    if len(tempfiles):
        info(f"Deleting all .{args.tempext} files")
        for tempfile in tempfiles:
            os.remove(args.outdir + "/" + tempfile)


# ---------------- test solutions ----------------


def get_result_file(
    out_file: str, temp_file: str, isvalidator: bool, force: str = "none"
) -> str:
    if isvalidator or force == "temp":
        return temp_file
    if not os.path.exists(out_file) or force == "out":
        return out_file
    return temp_file


def get_output_creation_message(output_file: str) -> str:
    reason = ("doesn't exist", "recompute")[os.path.exists(output_file)]
    return f"File {output_file} will be created now ({reason})."


def general_run_sol(
    sol: Solution,
    ifile: str,
    ofile: str,
    rfile: str,
    checker: Checker,
    cleartemp: bool,
    *rargs: Any,
) -> None:
    try:
        sol.run(ifile, ofile, rfile, checker, *rargs)
        if cleartemp and ofile != rfile and os.path.exists(rfile):
            os.remove(rfile)
    except Exception as err:
        traceback.print_exc()
        fatal(repr(err))


def test_all(
    solutions: Sequence[Solution | Validator],
    checker: Checker,
    inputs: Sequence[str],
    threads: int,
    args: ArgsTester,
) -> None:
    """
    First solution generates output file if it doesn't exist. All the other
    solutions can run in parallel however, they can't be checked via the Checker
    unless the output file is generated. They wait for Event, which is triggered
    when the generating solution thread finishes.

    The logs from all the threads are stored separately. Whenever a thread
    finishes, the corresponding logger closes and triggers an Event.
    Subsequently, the main thread reads as many of the closed logs as possible
    and prints them.
    """
    parallel_logger_manager = ParallelLoggerManager()

    def logger_close_and_trigger(logger: BufferedLogger) -> None:
        logger.close()
        parallel_logger_manager.closed_event.set()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        register_quit_with_executor(executor)
        executor._work_queue = TaskQueue(TASK_HISTORY)
        for input in inputs:
            input_file = args.indir + "/" + input
            prefix = args.outdir + "/" + input.rsplit(".", 1)[0]
            output_file = prefix + "." + args.outext
            temp_file = prefix + ".s{:0>2}." + args.tempext

            testcase_logger = parallel_logger_manager.get_sink()
            if len(solutions) > 1:
                testcase_logger.info(f"{input} >")

            def run_sol(
                sol: Solution,
                rfile: str,
                *rargs: Any,
                ifile: str = input_file,
                ofile: str = output_file,
                checker: Checker = checker,
                cleartemp: bool = args.cleartemp,
            ) -> None:
                general_run_sol(sol, ifile, ofile, rfile, checker, cleartemp, *rargs)

            output_ready = checker.output_ready[input_file]
            output_ready.clear()
            generated_output = False
            for si, sol in enumerate(solutions):
                result_force = (
                    "temp" if generated_output else "out" if args.reset else "none"
                )
                result_file = get_result_file(
                    output_file,
                    temp_file.format(si),
                    isinstance(sol, Validator),
                    result_force,
                )

                is_generator = result_file == output_file
                logger = parallel_logger_manager.get_sink()
                batch = Solution.parse_batch(input)
                task_item = TaskItem(sol.name, batch, input, run_sol)
                future = executor.submit(
                    task_item, sol, result_file, is_generator, logger
                )
                if is_generator:
                    testcase_logger.infob(get_output_creation_message(output_file))
                    generated_output = True
                    future.add_done_callback(lambda _, o=output_ready: o.set())
                future.add_done_callback(
                    lambda _, log=logger: logger_close_and_trigger(log)
                )

            if not generated_output:
                output_ready.set()
            logger_close_and_trigger(testcase_logger)

        while parallel_logger_manager.last_open < len(parallel_logger_manager.sinks):
            parallel_logger_manager.closed_event.wait()
            parallel_logger_manager.closed_event.clear()
            plain(parallel_logger_manager.read_closed())

    register_quit_signal()
    default_logger.statistics += parallel_logger_manager.statistics


def print_summary(
    solutions: Sequence[Solution | Validator], inputs: Sequence[str]
) -> None:
    print(get_statistics_header(inputs))
    for s in solutions:
        print(s.get_statistics())


# --------------------- FLOW ---------------------


def main() -> None:
    args = parse_args()
    if args.colortest:
        color_test()
        quit()
    setup_config(
        args,
        (
            "progdir",
            "pythoncmd",
            "fskip",
            "memorylimit",
            "quiet",
            "compile",
            "execute",
        ),
    )
    Config.rus_time = args.rustime and bool(shutil.which(Config.os_config.cmd_time))
    Config.timelimits.update(parse_timelimit(args.timelimit))
    Config.warn_timelimits.update(
        parse_warntimelimit(args.warntimelimit, Config.timelimits)
    )

    os.system(f"{Config.os_config.cmd_python} --version")

    files = get_relevant_prog_files_deeper(args.programs)
    solutions, checker_files = create_programs_from_files(files, not args.dupprog)
    checker = create_checker(args.diffcmd, checker_files, args.showdiffoutput)
    if args.sort:
        solutions.sort()
    programs = [checker] + solutions

    if args.clearbin:
        atexit.register(lambda p=programs: cleanup(p))

    prepare_programs(programs, max(4, args.threads))
    # multiple solutions can have same run command after compilation
    if not args.dupprog:
        solutions = deduplicate_solutions(solutions)

    for s in solutions:
        Config.cmd_maxlen = max(Config.cmd_maxlen, len(s.name))
    Config.inside_oneline = len(solutions) <= 1
    print_solutions_run_commands(solutions)

    inputs = get_inputs(args)
    _outputs = get_outputs(inputs, args)
    temp_clear(args)
    Config.inside_inputmaxlen = max(map(len, inputs)) if inputs else 0

    test_all(solutions, checker, inputs, args.threads, args)
    if args.stats:
        print_summary(solutions, inputs)

    check_data_folder_size(args.outdir)
    info(str(default_logger.statistics))

    if args.json:
        output = []
        for sol in solutions:
            output.append(sol.get_json())
        with open(args.json, "w") as f:
            json.dump(output, f, default=serialize_for_json)


if __name__ == "__main__":
    main()
