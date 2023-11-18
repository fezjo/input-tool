import threading
import time
from typing import Optional


class TaskHistory:
    """
    Keep track of which tasks are running, by whom, on what input, how long, ...
    Thread safe
    """

    # dict {program: {(batch, task): (start_time, end_time), ...}, ...}
    task_dict_t = dict[str, dict[tuple[str, str], tuple[float, Optional[float]]]]

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.tasks: TaskHistory.task_dict_t = {}

    def start(
        self, program: str, batch: str, task: str, start_time: Optional[float] = None
    ) -> None:
        start_time = time.time() if start_time is None else start_time
        with self.lock:
            if program not in self.tasks:
                self.tasks[program] = {}
            self.tasks[program][(batch, task)] = (start_time, None)

    def end(
        self, program: str, batch: str, task: str, end_time: Optional[float] = None
    ) -> None:
        end_time = time.time() if end_time is None else end_time
        key = (batch, task)
        if program not in self.tasks or key not in self.tasks[program]:
            return
        start_time, _ = self.tasks[program][key]
        with self.lock:
            self.tasks[program][key] = (start_time, end_time)

    def get(
        self, program: str, batch: str, task: str
    ) -> Optional[tuple[float, Optional[float]]]:
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
    ) -> list[tuple[str, str, str, float, Optional[float]]]:
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
                times = self.tasks[program][key]
                # print(running, times[1] is None)
                if running is not None and running != (times[1] is None):
                    continue
                result.append((program,) + key + self.tasks[program][key])
        return result


TASK_HISTORY = TaskHistory()
