# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
# Various types of messages with colors
from __future__ import annotations

import os
import re
import signal
import sys
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Sequence, TextIO, TypeVar, Union

from tqdm import tqdm


def register_quit_signal() -> None:
    signal.signal(signal.SIGUSR1, lambda *_: sys.exit(1))


register_quit_signal()


class Status(Enum):
    ok = 1, False
    tok = 1, True
    wa = 2, False
    twa = 2, True
    tle = 3, None
    exc = 4, False
    texc = 4, True
    ce = 5, None  # not used yet
    err = 6, None
    valid = 7, None

    @property
    def id(self) -> int:
        return self.value[0]

    @property
    def warntle(self) -> Union[bool, None]:
        return self.value[1]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Status) and self.id == other.id

    def __hash__(self) -> int:
        return super().__hash__()

    def set_warntle(self, state: Union[bool, None] = True) -> Status:
        return Status((self.id, None if self.warntle is None else state))

    def __str__(self) -> str:
        return status_reprs[self]

    def colored(self, end: Any = None) -> str:
        return "%s%s%s" % (Color.status[self], self, end or Color.normal)


status_reprs = {
    Status.ok: "OK",
    Status.tok: "tOK",
    Status.wa: "WA",
    Status.twa: "tWA",
    Status.tle: "TLE",
    Status.exc: "EXC",
    Status.texc: "tEXC",
    Status.ce: "CE",
    Status.err: "ERR",
    Status.valid: "VALID",
}


class Color:
    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    colorful = False
    dim: Color
    normal: Color
    infog: Color
    infob: Color
    warning: Color
    error: Color
    table: Color
    scores: list[Color]
    status: dict[Status, Color]

    @staticmethod
    def setup(colorful: bool) -> None:
        Color.colorful = colorful
        Color.dim = Color("dim")
        Color.normal = Color("normal")
        Color.infog = Color("good")
        Color.infob = Color("fine")
        Color.warning = Color("bad")
        Color.error = Color("error")
        Color.table = Color("blue")
        Color.scores = [Color("special1", "special2", "score%s" % i) for i in range(5)]
        Color.status = {s: Color(str(s)) for s in Status}

    def __init__(self, *args: str):
        if Color.colorful:
            modifiers = [str(_codemap[c]) for c in args]
            self.code = "\033[%sm" % ";".join(modifiers)
        else:
            self.code = ""

    def __str__(self) -> str:
        return self.code

    @staticmethod
    def score_color(points: float, maxpoints: float) -> Color:
        bounds = [0, 4, 7, 9, 10]
        p = 0
        while p < 4 and points * 10 > maxpoints * bounds[p]:
            p += 1
        return Color.scores[p]

    @staticmethod
    def status_colorize(status: Status, text: Any, end: Optional[Color] = None) -> str:
        color = Color.infog if status in (Status.ok, Status.valid) else Color.warning
        return Color.colorize(text, color, end)

    @staticmethod
    def colorize(text: Any, color: Color, end: Optional[Color] = None) -> str:
        lines = str(text).split("\n")
        end = end or Color.normal
        return "\n".join("%s%s%s" % (color, line, end) for line in lines)

    @staticmethod
    def uncolorize(text: str) -> str:
        return Color.ANSI_ESCAPE.sub("", text)


_codemap: dict[str, str | int] = {
    "OK": "green",
    "tOK": "green",
    "WA": "red",
    "tWA": "red",
    "TLE": "purple",
    "EXC": 45,
    "tEXC": 45,
    "CE": "ERR",
    "ERR": 41,
    "VALID": "OK",
    "bad": "yellow",
    "good": "green",
    "ok": "yellow",
    "fine": "blue",
    "error": "ERR",
    "score0": 196,
    "score1": 208,
    "score2": 226,
    "score3": 228,
    "score4": 46,
    "red": 91,
    "green": 92,
    "yellow": 93,
    "blue": 94,
    "purple": 95,
    "cyan": 96,
    "white": 37,
    "bold": 1,
    "dim": 2,
    "underlined": 4,
    "blink": 5,
    "invert": 7,
    "nobold": 21,
    "nodim": 22,
    "nounderlined": 24,
    "noblink": 25,
    "noinvert": 27,
    "normal": 0,
    "special1": 38,
    "special2": 5,
}

# compile _codemap
_changed = True
while _changed:
    _changed = False
    for key in _codemap:
        key2 = _codemap[key]
        if isinstance(key2, str):
            _codemap[key] = _codemap[key2]
            _changed = True


Color.setup(True)

# {{{ ---------------------- progress bar ------------------------


def stylized_tqdm(desc: str, total: int, **kwargs: Any) -> tqdm:
    cnt_len = len(str(total))
    fields = (
        Color.colorize("{desc}", Color("bold", "white")),
        Color.colorize("│{bar}│", Color("cyan")),
        Color.colorize("{percentage:3.0f}%", Color("purple")),
        Color.colorize("{n_fmt:>" + str(cnt_len) + "}/{total_fmt}", Color("green")),
        Color.colorize("{elapsed} ", Color("yellow")),
    )
    bar_format = " ".join(fields)
    # TODO autorefresh
    return tqdm(desc=desc, total=total, bar_format=bar_format, **kwargs)


# {{{ ---------------------- messages ----------------------------


def plural(n: int, s: str) -> str:
    return f"{n} {s}" if n == 1 else f"{n} {s}s"


@dataclass
class LoggerStatistics:
    warnings: int = 0
    errors: int = 0

    def __str__(self) -> str:
        info_color = Color("normal", "blue" if self.warnings + self.errors else "green")
        error_msg = Color.colorize(
            plural(self.errors, "error"),
            Color.error if self.errors else info_color,
            info_color,
        )
        warning_msg = Color.colorize(
            plural(self.warnings, "warning"),
            Color.warning if self.warnings else info_color,
            info_color,
        )
        msg = Color.colorize(
            f"During execution there were {error_msg} and {warning_msg}.", info_color
        )
        return msg

    def __add__(self, other: LoggerStatistics) -> LoggerStatistics:
        return LoggerStatistics(
            warnings=self.warnings + other.warnings,
            errors=self.errors + other.errors,
        )


class Logger:
    def __init__(self, file: TextIO = sys.stderr):
        self.file = file
        self.statistics = LoggerStatistics()

    def write(self, text: Any, end: str = "\n") -> None:
        self.file.write(text + end)

    def fatal(self, text: Any) -> None:
        self.error(text)
        os.kill(os.getpid(), signal.SIGUSR1)
        # quit(1)

    def error(self, text: Any) -> None:
        self.statistics.errors += 1
        self.write(Color.colorize(text, Color.error))

    def warning(self, text: Any) -> None:
        self.statistics.warnings += 1
        self.write(Color.colorize(text, Color.warning))

    # blue
    def infob(self, text: Any) -> None:
        self.write(Color.colorize(text, Color.infob))

    # green
    def infog(self, text: Any) -> None:
        self.write(Color.colorize(text, Color.infog))

    def infod(self, text: Any) -> None:
        """without newline"""
        self.write(Color.colorize(text, Color.dim), "")

    def info(self, text: Any) -> None:
        self.write(text)

    def plain(self, text: Any) -> None:
        """without newline"""
        self.write(text, "")


default_logger = Logger(sys.stdout)
fatal = default_logger.fatal
error = default_logger.error
warning = default_logger.warning
infob = default_logger.infob
infog = default_logger.infog
infod = default_logger.infod
info = default_logger.info
plain = default_logger.plain


class BufferedLogger(Logger):
    def __init__(self, file: TextIO = sys.stderr):
        super().__init__(file)
        self.buffer: list[str] = []
        self.open = True

    def error(self, text: Any, *, flush: bool = True) -> None:
        super().error(text)
        if flush:
            self.flush()

    def write(self, text: Any, end: str = "\n") -> None:
        self.buffer.append(text + end)

    def read(self) -> str:
        return "".join(self.buffer)

    def flush(self) -> None:
        self.file.write(self.read())
        self.buffer.clear()

    def close(self) -> None:
        self.open = False


class ParallelLoggerManager:
    def __init__(self) -> None:
        self.sinks: list[BufferedLogger] = []
        self.last_open = 0
        self.closed_event = threading.Event()
        self.statistics = LoggerStatistics()

    def get_sink(self) -> BufferedLogger:
        self.sinks.append(BufferedLogger())
        return self.sinks[-1]

    def clear_buffers(self) -> None:
        for c in self.sinks:
            c.buffer.clear()

    def read_closed(self) -> str:
        res: list[str] = []
        while self.last_open < len(self.sinks):
            sink = self.sinks[self.last_open]
            if sink.open:
                break
            res.append(sink.read())
            self.statistics += sink.statistics
            self.last_open += 1
        return "".join(res)


# }}}


def table_row(
    color: Color,
    columns: Sequence[Any],
    widths: Sequence[int],
    alignments: Sequence[str],
) -> str:
    assert len(columns) == len(widths) == len(alignments)
    columns = list(columns)
    for i in range(len(columns)):
        width, align, value = widths[i], alignments[i], columns[i]
        if isinstance(value, Status):
            value = value.colored()
        width += len(str(value)) - len(Color.uncolorize(str(value)))
        text = f"{value:{align}{width}}"
        columns[i] = Color.colorize(text + str(Color.normal), color, Color.table)
    return Color.colorize("| %s |" % " | ".join(columns), Color.table)


def table_header(
    columns: Sequence[Any], widths: Sequence[int], alignments: Sequence[str]
) -> str:
    first_row = table_row(Color.table, columns, widths, alignments)
    second_row = "|".join(
        [str(Color.table)] + ["-" * (w + 2) for w in widths] + [str(Color.normal)]
    )
    return f"{first_row}\n{second_row}"


def color_test() -> None:
    Color.setup(True)

    info("white")
    infob("blue")
    infog("green")
    warning("warning")
    error("error")
    sys.stderr.write(" ".join([s.colored() for s in Status]) + "\n")
    for i in range(11):
        sys.stderr.write(Color.colorize(f"{i}/10\n", Color.score_color(i, 10)))


Concatable = TypeVar("Concatable", list[Any], tuple[Any, ...], str)


def ellipsis(items: Concatable, max_length: int, indicator: Concatable) -> Concatable:
    if len(items) <= max_length:
        return items
    assert max_length > len(indicator)
    remaining = max_length - len(indicator)
    half, asym = remaining // 2, remaining % 2
    if half > 0:
        return items[: half + asym] + indicator + items[-half:]
    return items[:remaining] + indicator


def fit_text_into_screen(text: str, height: int, width: int = 80) -> str:
    lines = text.splitlines(True)
    vertically_fit = ellipsis(lines, height, ["...\n"])
    fit = (ellipsis(line, width, "...") for line in vertically_fit)
    return "".join(fit)


def side_by_side(text1: str, text2: str, height: int, width: int = 80) -> str:
    half_width = (width - 3) // 2
    lines1 = fit_text_into_screen(text1, height, half_width).splitlines()
    lines2 = fit_text_into_screen(text2, height, half_width).splitlines()
    res: list[str] = []
    for i in range(max(len(lines1), len(lines2))):
        line1 = lines1[i] if i < len(lines1) else " " * half_width
        line2 = lines2[i] if i < len(lines2) else " " * half_width
        # = if the same, ! if not the same, > if line1 is empty, < if line2 is empty
        delim = (
            "=" if line1 == line2 else "!" if line1 and line2 else ">" if line1 else "<"
        )
        res.append(f"{line1} {delim} {line2}")
    return "\n".join(res)


def serialize_for_json(obj: Any) -> Any:
    if isinstance(obj, (list, tuple, set)):
        return [serialize_for_json(o) for o in obj]
    if isinstance(obj, dict):
        return {serialize_for_json(k): serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)
