# © 2023 fezjo
import threading
import time
from dataclasses import dataclass
from subprocess import Popen
from typing import Callable, Optional


class TaskHistory:
    """
    Keep track of which tasks are running, by whom, on what input, how long, ...
    Thread safe
    """

    @dataclass
    class task_details_t:
        start_time: float
        end_time: Optional[float] = None
        process: Optional[Popen] = None
        skipped: bool = False
        killed: bool = False

    # dict {program: {(batch, task): (start_time, end_time), ...}, ...}
    task_dict_t = dict[str, dict[tuple[str, str], task_details_t]]
    callbacks_t = tuple[Callable[[Popen], None], Callable[[], bool], Callable[[], None]]

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.tasks: TaskHistory.task_dict_t = {}

    def start(
        self, program: str, batch: str, task: str, start_time: Optional[float] = None
    ) -> None:
        """call when as soon as the task execution starts so that it may be killed"""
        start_time = time.time() if start_time is None else start_time
        with self.lock:
            if program not in self.tasks:
                self.tasks[program] = {}
            self.tasks[program][(batch, task)] = TaskHistory.task_details_t(start_time)

    def end(
        self,
        program: str,
        batch: str,
        task: str,
        end_time: Optional[float] = None,
        skipped: bool = False,
    ) -> None:
        """call as soon as soon the task execution ends, so that it won't be killed"""
        end_time = time.time() if end_time is None else end_time
        key = (batch, task)
        if program not in self.tasks or key not in self.tasks[program]:
            return
        with self.lock:
            self.tasks[program][key].end_time = end_time
            self.tasks[program][key].skipped = skipped

    def get(self, program: str, batch: str, task: str) -> Optional[task_details_t]:
        key = (batch, task)
        if program not in self.tasks or key not in self.tasks[program]:
            return None
        return self.tasks[program][key]

    def get_all(
        self,
        program: Optional[str] = None,
        batch: Optional[str] = None,
        task: Optional[str] = None,
        running: Optional[bool] = None,
    ) -> list[tuple[str, str, str, task_details_t]]:
        result = []
        if program is None:
            for program in self.tasks:
                result += self.get_all(program, batch, task, running)
        else:
            if program not in self.tasks:
                return []
            for key in self.tasks[program]:
                if batch is not None and key[0] != batch:
                    continue
                if task is not None and key[1] != task:
                    continue
                detail = self.tasks[program][key]
                if running is not None and running != (detail.end_time is None):
                    continue
                result.append((program, *key, detail))
        return result

    def get_callbacks(self, program: str, batch: str, task: str) -> callbacks_t:
        key = (batch, task)
        if program not in self.tasks or key not in self.tasks[program]:
            raise ValueError(f"Task {program} {batch} {task} not found")
        detail = self.tasks[program][key]
        return (
            lambda process: setattr(detail, "process", process),
            lambda: getattr(detail, "killed"),
            lambda: self.kill_all(program, batch),
        )

    def kill_all(
        self,
        program: Optional[str] = None,
        batch: Optional[str] = None,
        task: Optional[str] = None,
    ) -> None:
        for program, batch, task, detail in self.get_all(
            program, batch, task, running=True
        ):
            if detail.process is not None:
                # elapsed = time.time() - detail.start_time
                # print("Killing", program, batch, task, round(elapsed, 4), "s")
                detail.process.kill()
                detail.killed = True


TASK_HISTORY = TaskHistory()
