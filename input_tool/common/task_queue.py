import threading
import time
import types
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

    def __repr__(self):
        return (
            f"TaskItem({self.program!r}, {self.batch!r}, {self.task!r}, {self.func!r})"
        )

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class TaskQueue(SimpleQueue):
    """Thread-safe Usually-First-In-First-Out queue. Based on queue.SimpleQueue.
    A task is a program. This same program can also already be running on a different
    input. If it is running too long (3/4 of the timelimit), we assume it will time out
    and running this task would be a waste of time. We can not know for sure if it will
    time out, so we need to keep it in consideration. We find first task that is not
    running too long or run the first in queue if no such task exists.
    The queue may contain None items, which are ignored.
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
        now = time.time()
        for prev_task in prev_tasks:
            print(curr_task, now - prev_task[3])
            if now - prev_task[3] > timelimit * 0.75:
                return True
        return False

    def __init__(self, task_history: TaskHistory):
        self._lock = threading.Lock()
        self._queue = deque()
        self._count = threading.Semaphore(0)
        self._task_history = task_history

    def __repr__(self) -> str:
        return f"TaskQueue({self._lock!r}, {self._count!r}, {len(self._queue)!r})"

    def put(self, item, block=True, timeout=None):
        """Put the item on the queue.

        The optional 'block' and 'timeout' arguments are ignored, as this method
        never blocks.  They are provided for compatibility with the Queue class.
        """
        with self._lock:
            self._queue.append(item)
        self._count.release()

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.

        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until an item is available. If 'timeout' is
        a non-negative number, it blocks at most 'timeout' seconds and raises
        the Empty exception if no item was available within that time.
        Otherwise ('block' is false), return an item if one is immediately
        available, else raise the Empty exception ('timeout' is ignored
        in that case).
        """
        if timeout is not None and timeout < 0:
            raise ValueError("'timeout' must be a non-negative number")
        res = None
        with self._lock:
            while self._queue and self._queue[0] is None:
                self._queue.popleft()
        if not self._count.acquire(block, timeout):
            raise Empty
        # TODO maybe this it was corrupted in the meantime, fix later
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
        """Put an item into the queue without blocking.

        This is exactly equivalent to `put(item, block=False)` and is only provided
        for compatibility with the Queue class.
        """
        return self.put(item, block=False)

    def get_nowait(self):
        """Remove and return an item from the queue without blocking.

        Only get an item if one is immediately available. Otherwise
        raise the Empty exception.
        """
        return self.get(block=False)

    def empty(self):
        """Return True if the queue is empty, False otherwise (not reliable!)."""
        return len(self._queue) == 0

    def qsize(self):
        """Return the approximate size of the queue (not reliable!)."""
        return len(self._queue)

    __class_getitem__ = classmethod(types.GenericAlias)
