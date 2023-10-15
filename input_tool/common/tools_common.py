import os
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, Sequence

from input_tool.common import os_config
from input_tool.common.commands import Config
from input_tool.common.messages import (
    Color,
    ParallelLoggerManager,
    default_logger,
    plain,
    warning,
)
from input_tool.common.parser import ArgsGenerator, ArgsTester
from input_tool.common.programs.program import Program


def setup_config(args: ArgsTester | ArgsGenerator, config_keys: Iterable[str]) -> None:
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


def cleanup(programs: Sequence[Program]) -> None:
    for p in programs:
        p.clear_files()
    if Config.progdir is not None:
        try:
            os.removedirs(Config.progdir)
        except OSError:
            warning(f"Program directory not empty {os.listdir(Config.progdir)}")


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
