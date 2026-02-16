# © 2023 fezjo
import threading
from typing import Callable, Optional, Reversible

from input_tool.common.commands import Config, Langs
from input_tool.common.task_history import TaskHistory


class TaskItem:
    def __init__(
        self,
        program: str,
        batch: str,
        task: str,
        func: Callable,
        callbacks: Optional[list[Callable]] = None,
    ):
        self.program = program
        self.batch = batch
        self.task = task
        self.func = func
        self.callbacks: list[Callable] = callbacks if callbacks is not None else []

    def __repr__(self) -> str:
        return (
            f"TaskItem({self.program!r}, {self.batch!r}, {self.task!r}, {self.func!r})"
        )

    def should_skip(self, task_history: TaskHistory) -> bool:
        lang = Langs.from_filename(self.program)
        timelimit = Config.get_timelimit(Config.timelimits, None, lang)
        if timelimit == 0:
            return False
        prev_tasks = task_history.get_all(self.program, self.batch, running=True)
        return bool(prev_tasks)


class TaskQueue:
    """
    Thread-safe Usually-First-In-First-Out queue.
    A task is a program running on an input. The same program can also already
    be running on a different input. If we deduce that the already running
    program might time out for some reason, running this task would be a waste
    of time. We can not know for sure if it will time out, so we need to keep it
    in the queue. We will find a task we think has a better chance of being
    relevant, or fall back on the first in queue if no such task exists.
    """

    def __init__(self, tasks: Reversible[TaskItem], task_history: TaskHistory):
        self._lock = threading.Lock()
        self._stack: list[TaskItem] = list(reversed(tasks))
        self._task_history = task_history

    def __len__(self) -> int:
        return len(self._stack)

    def pop(self) -> Optional[TaskItem]:
        """Return a task that is not likely to be blocked by a previous task, or None if queue is empty."""
        with self._lock:
            if not self._stack:
                return None
            for i in range(-1, -len(self._stack) - 1, -1):
                if self._stack[i].should_skip(self._task_history):
                    continue
                return self._stack.pop(i)
            # there is no unblocked task, so we will just take the first one, even if it is blocked
            return self._stack.pop()
