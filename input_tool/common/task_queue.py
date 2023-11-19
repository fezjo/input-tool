import threading
from collections import deque
from queue import SimpleQueue
from typing import Callable

from input_tool.common.commands import Config, Langs
from input_tool.common.task_history import TaskHistory


class Empty(Exception):
    "Exception raised by Queue.get(block=0)/get_nowait()."
    pass


class TaskItem:
    def __init__(self, program: str, batch: str, task: str, func: Callable):
        self.program = program
        self.batch = batch
        self.task = task
        self.func = func

    def __repr__(self) -> str:
        return (
            f"TaskItem({self.program!r}, {self.batch!r}, {self.task!r}, {self.func!r})"
        )

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class TaskQueue(SimpleQueue):
    """Thread-safe Usually-First-In-First-Out queue. Based on queue.SimpleQueue.
    A task is a program running on an input. The same program can also already
    be running on a different input. If we deduce that the already running
    program might time out for some reason, running this task would be a waste
    of time. We can not know for sure if it will time out, so we need to keep it
    in the queue. We will find a task we think has a better change of being
    relevant, or fall back on the first in queue if no such task exists. Because
    of this out of order picking, the queue may contain None items, which will
    be ignored.
    """

    @staticmethod
    def skip(curr_task: TaskItem, task_history: TaskHistory) -> bool:
        lang = Langs.from_filename(curr_task.program)
        timelimit = Config.get_timelimit(Config.timelimits, None, lang)
        if timelimit == 0:
            return False
        prev_tasks = task_history.get_all(
            curr_task.program, curr_task.batch, running=True
        )
        return bool(prev_tasks)

    def __init__(self, task_history: TaskHistory):
        self._lock = threading.Lock()
        self._queue: deque[TaskItem | None] = deque()
        self._count = threading.Semaphore(0)
        self._task_history = task_history

    def __repr__(self) -> str:
        return f"TaskQueue({self._lock!r}, {self._count!r}, {len(self._queue)!r})"

    def put(self, item, block=True, timeout=None):
        with self._lock:
            self._queue.append(item)
        self._count.release()

    def get(self, block=True, timeout=None):
        if timeout is not None and timeout < 0:
            raise ValueError("'timeout' must be a non-negative number")
        res = None
        with self._lock:
            while self._queue and self._queue[0] is None:
                self._queue.popleft()
        if not self._count.acquire(block, timeout):
            raise Empty
        # TODO maybe it was corrupted in the meantime, fix later
        with self._lock:
            for i, work_item in enumerate(self._queue):
                if work_item is None:
                    continue
                if not self.skip(work_item.fn, self._task_history):
                    if i:
                        res = work_item
                        self._queue[i] = None
                    break
            if res is None:
                res = self._queue.popleft()
        return res

    def put_nowait(self, item):
        return self.put(item, block=False)

    def get_nowait(self):
        return self.get(block=False)

    def empty(self):
        """Return True if the queue is empty, False otherwise (not reliable!)."""
        return len(self._queue) == 0

    def qsize(self):
        """Return the approximate size of the queue (not reliable! use self._lock)."""
        return len(self._queue)
