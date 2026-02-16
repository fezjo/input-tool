#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
# Complex script that can test solutions
import atexit
import json
import os
import shutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Callable, Iterable, Optional, Sequence, Union

from input_tool.common.commands import (
    Config,
    Langs,
    get_statistics_header,
    natural_sort_key,
)
from input_tool.common.messages import (
    BufferedLogger,
    Logger,
    ParallelLoggerManager,
    Status,
    default_logger,
    fatal,
    info,
    infob,
    plain,
    register_quit_signal,
    serialize_for_json,
    stylized_tqdm,
    warning,
)
from input_tool.common.parser.parser import Parser
from input_tool.common.parser.specifications import (
    ArgsTester,
    description_tester,
    options_tester,
)
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
from input_tool.common.types import Directory, Path, RelativePath, TempFile

# ----------------- configuration ----------------


def parse_args() -> ArgsTester:
    parser = Parser(description_tester, options_tester)
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


def get_relevant_prog_files_in_directory(directory: Directory) -> list[Path]:
    classes = (Solution, Validator, Checker)
    return [
        path
        for path in directory.iterdir()
        if path.is_file() and any(cl.filename_befits(path.name) for cl in classes)
    ]


def get_relevant_prog_files_deeper(candidates: Iterable[str]) -> list[Path]:
    subresults = (
        get_relevant_prog_files_in_directory(p) if p.is_dir() else [p]
        for p in map(Path, candidates)
    )
    return sum(subresults, [])


def create_programs_from_files(
    files: Iterable[Path], deduplicate: bool
) -> tuple[list[Union[Solution, Validator]], list[Path]]:
    solutions: list[Union[Solution, Validator]] = []
    checker_files: list[Path] = []
    if deduplicate:  # remove duplicate paths keeping order
        files = list(dict.fromkeys(files))
    for p in files:
        if Validator.filename_befits(p.name):
            solutions.append(Validator(str(p)))
        elif Checker.filename_befits(p.name):
            checker_files.append(p)
        else:
            solutions.append(Solution(str(p)))
    return solutions, checker_files


def create_checker(
    checker_files: Sequence[str], default_checker: str, show_diff_output: bool
) -> Checker:
    if default_checker:
        checker_files = [default_checker]
    if len(checker_files) > 1:
        fatal(
            f"More than one checker found {checker_files}.\n"
            "Set explicitly with -d/--diffcmd (e.g. -d diff) "
            "or leave only one checker in the directory."
        )
    return Checker(checker_files[0], show_diff_output)


def deduplicate_solutions(
    solutions: Iterable[Union[Solution, Validator]],
) -> list[Union[Solution, Validator]]:
    d: dict[str, Program] = {}
    res: list[Union[Solution, Validator]] = []
    for s in solutions:
        key = s.run_cmd
        assert key is not None
        if key in d:
            warning(
                f"Solution {d[key].name} and {s.name} have the same run command. "
                "Keeping only first."
            )
        else:
            d[key] = s
            res.append(s)
    return res


def print_solutions_run_commands(
    solutions: Iterable[Union[Solution, Validator]],
) -> None:
    infob("----- Run commands -----")
    for s in solutions:
        infob(f"Program {s.name:{Config.cmd_maxlen}}   is ran as `{s.run_cmd}`")
    infob("------------------------")


# --------------- prepare io files ---------------


def sorted_files_with_ext(
    dir: Directory, ext: str, key: Optional[Callable] = None
) -> list[Path]:
    ext = f".{ext.lstrip('.')}"
    return sorted(
        (Path(f.name) for f in dir.iterdir() if f.suffix == ext),
        key=key,
    )


def get_inputs(args: ArgsTester) -> list[RelativePath]:
    if not args.indir.exists():
        fatal(f"Input directory `{args.indir}` doesn't exist.")
    return sorted_files_with_ext(
        args.indir, args.inext, lambda p: natural_sort_key(str(p))
    )


def get_outputs(
    inputs: Sequence[Path], args: ArgsTester
) -> Optional[list[RelativePath]]:
    if not args.outdir.exists():
        args.outdir.mkdir(parents=True)
    if args.outext != args.tempext and not args.reset:
        outputs = sorted_files_with_ext(args.outdir, args.outext)
        if len(outputs) > 0 and len(outputs) < len(inputs):
            warning("Incomplete output files.")
        return outputs
    else:
        infob("Outputs will be regenerated")
        return None


def temp_clear(args: ArgsTester) -> None:
    tempfiles = sorted_files_with_ext(args.outdir, args.tempext)
    if len(tempfiles):
        info(f"Deleting all .{args.tempext} files")
        for tempfile in tempfiles:
            (args.outdir / tempfile).unlink()


def setup_ioram(
    args: ArgsTester, inputs: list[RelativePath], _outputs: Optional[list[RelativePath]]
) -> None:
    ramdir = Directory("/dev/shm/input_tool/{0}".format(os.getpid()))
    try:
        ramdir.mkdir(parents=True)
    except Exception as e:
        fatal(f"Failed to create ramdir {ramdir}: {e!r}")
    infob(f"Using {ramdir} for input and output files.")
    for input in inputs:
        shutil.copy(args.indir / input, ramdir / input)
    for output in _outputs or []:
        shutil.copy(args.outdir / output, ramdir / output)
    args.indir = ramdir
    args.outdir = ramdir
    atexit.register(lambda: shutil.rmtree(ramdir))


# ---------------- test solutions ----------------


def get_result_file(
    out_file: Path,
    temp_file: TempFile,
    isvalidator: bool,
    force: str = "none",
) -> Path:
    if isvalidator or force == "temp":
        return temp_file
    if not out_file.exists() or force == "out":
        return out_file
    return temp_file


def get_output_creation_message(output_file: Path) -> str:
    reason = ("doesn't exist", "recompute")[output_file.exists()]
    return f"File {output_file} will be created now ({reason})."


def run_sol(
    sol: Union[Solution, Validator],
    ifile: Path,
    ofile: Path,
    rfile: TempFile,
    checker: Checker,
    cleartemp: bool,
    is_output_generator: bool,
    logger: Optional[Logger] = None,
) -> None:
    try:
        sol.run(ifile, ofile, rfile, checker, is_output_generator, logger)
        if cleartemp and ofile != rfile and rfile.exists():
            rfile.unlink()
    except Exception as e:
        traceback.print_exc()
        fatal(repr(e))


def build_test_tasks(
    solutions: Sequence[Union[Solution, Validator]],
    checker: Checker,
    inputs: Sequence[RelativePath],
    args: ArgsTester,
    parallel_logger_manager: ParallelLoggerManager,
    logger_finalize: Callable[[BufferedLogger], None],
) -> list[TaskItem]:
    tasks: list[TaskItem] = []
    for input in inputs:
        input_file = args.indir / input
        prefix = str(args.outdir / input.with_suffix(""))
        output_file = Path(prefix + "." + args.outext)
        temp_file_template = prefix + ".s{:0>2}." + args.tempext

        testcase_logger = parallel_logger_manager.get_sink()
        if len(solutions) > 1:
            testcase_logger.info(f"{input} >")

        output_ready = checker.output_ready[input_file]
        output_ready.clear()
        generating_output = False
        for si, sol in enumerate(solutions):
            result_force = (
                "temp" if generating_output else "out" if args.reset else "none"
            )
            result_file = get_result_file(
                output_file,
                Path(temp_file_template.format(si)),
                isinstance(sol, Validator),
                result_force,
            )

            is_generator = result_file == output_file
            logger = parallel_logger_manager.get_sink()
            batch = Solution.parse_batch(input)
            callbacks: list[Callable] = []
            if is_generator:
                testcase_logger.infob(get_output_creation_message(output_file))
                generating_output = True
                callbacks.append(lambda _, o=output_ready: o.set())

            callbacks.append(lambda _, logger=logger: logger_finalize(logger))

            def run_task(
                sol=sol,
                ifile=input_file,
                ofile=output_file,
                rfile=result_file,
                checker=checker,
                cleartemp=args.cleartemp,
                is_generator=is_generator,
                logger=logger,
            ):
                run_sol(
                    sol, ifile, ofile, rfile, checker, cleartemp, is_generator, logger
                )

            task_item = TaskItem(sol.name, batch, str(input), run_task, callbacks)
            tasks.append(task_item)

        if not generating_output:
            output_ready.set()
        logger_finalize(testcase_logger)

    return tasks


def run_task_queue(
    queue: TaskQueue,
    num_threads: int,
    parallel_logger_manager: ParallelLoggerManager,
) -> None:
    with stylized_tqdm(desc="Testing", total=len(queue)) as progress_bar:
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            register_quit_with_executor(executor)

            def get_new_task(_=None):
                task = queue.pop()
                if task is None:
                    return
                task.callbacks.append(lambda _, p=progress_bar: p.update())
                try:
                    future = executor.submit(task.func)
                except RuntimeError:
                    for callback in task.callbacks:
                        callback(None)
                    # don't submit new tasks if executor is already shutting down
                else:
                    for callback in task.callbacks:
                        future.add_done_callback(callback)
                    future.add_done_callback(get_new_task)

            for _ in range(num_threads):
                executor.submit(get_new_task)

            while parallel_logger_manager.last_open < len(
                parallel_logger_manager.sinks
            ):
                parallel_logger_manager.closed_event.wait()
                parallel_logger_manager.closed_event.clear()
                progress_bar.clear()
                plain(parallel_logger_manager.read_closed())
                progress_bar.display()


def test_all(
    solutions: Sequence[Union[Solution, Validator]],
    checker: Checker,
    inputs: Sequence[RelativePath],
    num_threads: int,
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

    def logger_finalize(logger: BufferedLogger) -> None:
        logger.close()
        parallel_logger_manager.closed_event.set()

    tasks = build_test_tasks(
        solutions,
        checker,
        inputs,
        args,
        parallel_logger_manager,
        logger_finalize,
    )
    queue = TaskQueue(tasks, TASK_HISTORY)
    run_task_queue(queue, num_threads, parallel_logger_manager)

    register_quit_signal()
    default_logger.statistics += parallel_logger_manager.statistics


def print_summary(
    solutions: Iterable[Union[Solution, Validator]], inputs: Iterable[RelativePath]
) -> None:
    info("")
    info(get_statistics_header(inputs))
    for s in solutions:
        info(s.get_statistics())


def check_too_long_tests(
    solutions: Iterable[Union[Solution, Validator]], timelitmit: timedelta
) -> None:
    accepted = [s for s in solutions if s.statistics.result == Status.ok]
    if not accepted:
        return
    fastest = min(s.statistics.maxtime for s in accepted)
    if fastest > timelitmit:
        seconds = round(fastest.total_seconds(), 2)
        warning(
            f"Fastest solution took {seconds}/{timelitmit.total_seconds()}s. "
            "Consider making smaller tests."
        )


# --------------------- FLOW ---------------------


def run(args: ArgsTester) -> None:
    setup_config(
        args,
        (
            "progdir",
            "pythoncmd",
            "fail_skip",
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
    Config.threads = args.threads if args.threads else Config.get_cpu_corecount(0.25)

    if 0 < Config.memorylimit < 100:
        warning(
            f"Memory limit ({Config.memorylimit}MB) is <100MB; "
            "this can cause Python to just crash!"
        )

    os.system(f"{Config.os_config.cmd_python} --version")

    files = get_relevant_prog_files_deeper(args.programs)
    solutions, checker_files = create_programs_from_files(files, not args.dupprog)
    if not checker_files and not args.diffcmd:
        args.diffcmd = "diff"
    checker = create_checker(
        tuple(map(str, checker_files)), args.diffcmd, args.showdiff
    )
    if args.sort:
        solutions.sort(reverse=True, key=lambda s: s.compare_mask())
    if args.bestonly:
        solutions = [s for s in solutions if isinstance(s, Validator)] + [
            s for s in solutions if not isinstance(s, Validator)
        ][:1]
    programs = [checker] + solutions

    def cleanup_programs() -> None:
        cleanup(programs)

    if args.clearbin:
        atexit.register(cleanup_programs)

    prepare_programs(programs, max(4, Config.threads))
    # multiple solutions can have same run command after compilation
    if not args.dupprog:
        solutions = deduplicate_solutions(solutions)

    for s in solutions:
        Config.cmd_maxlen = max(Config.cmd_maxlen, len(s.name))
    Config.inside_oneline = len(solutions) <= 1
    print_solutions_run_commands(solutions)

    inputs = get_inputs(args)
    _outputs = get_outputs(inputs, args)
    if args.ioram:
        setup_ioram(args, inputs, _outputs)

    temp_clear(args)
    Config.inside_inputmaxlen = max(len(str(p)) for p in inputs) if inputs else 0

    test_all(solutions, checker, inputs, Config.threads, args)
    if args.stats:
        print_summary(solutions, inputs)

    info("")
    check_data_folder_size(args.outdir)
    check_too_long_tests(solutions, timedelta(seconds=1))
    info(str(default_logger.statistics))

    if args.json:
        output = []
        for sol in solutions:
            output.append(sol.get_json())
        with open(args.json, "w") as f:
            json.dump(output, f, default=serialize_for_json)

    # TODO check if parallel testing slows down the testing
    if Config.threads > 1:
        infob(
            "Make sure to verify whether parallel testing significantly "
            "impacts the program's execution speed."
        )


def main():
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
