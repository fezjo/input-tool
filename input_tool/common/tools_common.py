# © 2023 fezjo
import atexit
import os
import signal
import sys
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Iterable, Sequence, Union

from input_tool.common import os_config
from input_tool.common.commands import Config
from input_tool.common.messages import (
    Color,
    ParallelLoggerManager,
    default_logger,
    plain,
    warning,
)
from input_tool.common.parser.specifications import (
    ArgsCompile,
    ArgsGenerator,
    ArgsTester,
)
from input_tool.common.programs.program import Program


def register_quit_with_executor(executor: Executor) -> None:
    def quit_with_executor(code: int) -> None:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception as e:
            warning(f"Exception while shutting down executor: {e!r}")
        sys.exit(code)

    signal.signal(signal.SIGUSR1, lambda *_: quit_with_executor(1))


def setup_config(
    args: Union[ArgsTester, ArgsGenerator, ArgsCompile], config_keys: Iterable[str]
) -> None:
    Color.setup(args.colorful)

    if args.deprecated:
        for option in args.deprecated:
            warning(f"Option '{option}' is deprecated.")

    Config.os_config = os_config.find_os_config()
    Config.os_config.cmd_python = os_config.find_pythoncmd(args.pythoncmd)
    Config.os_config.check_all_os_utils_exist()

    for key in config_keys:
        setattr(Config, key, getattr(args, key))

    if not Config.progdir:
        Config.progdir = None
    else:
        os.makedirs(Config.progdir, exist_ok=True)


@atexit.register
def cleanup_progdir(warn: bool = False) -> None:
    if Config.progdir is None:
        return
    try:
        os.removedirs(Config.progdir)
    except OSError:
        if warn:
            warning(f"Program directory not empty {os.listdir(Config.progdir)}")


def cleanup(programs: Sequence[Program]) -> None:
    for p in programs:
        p.clear_files()
    cleanup_progdir(True)


def prepare_programs(programs: Iterable[Program], threads: int) -> None:
    parallel_logger_manager = ParallelLoggerManager()
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [
            executor.submit(p.prepare, parallel_logger_manager.get_sink())
            for p in programs
        ]
        for future, logger in zip(futures, parallel_logger_manager.sinks):
            future.result()
            plain(logger.read())
        parallel_logger_manager.clear_buffers()
    default_logger.statistics += parallel_logger_manager.statistics


def check_data_folder_size(path: str, max_size_mb: int = 42) -> None:
    if not os.path.exists(path):
        return
    # get total size of all files in the directory recursively
    total_size_b = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:  # includes links
            fp = os.path.join(dirpath, f)
            total_size_b += os.path.getsize(fp)
    total_size_mb = round(total_size_b / 1024**2, 2)
    if total_size_mb > max_size_mb:
        warning(
            f"Data folder '{path}' exceeds maximum recommended size: "
            f"{total_size_mb}/{max_size_mb}MB"
        )
