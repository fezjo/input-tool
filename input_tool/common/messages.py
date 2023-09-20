# (c) 2014 jano <janoh@ksp.sk>
# Various types of messages with colors
from __future__ import annotations
from enum import Enum
import sys
import threading
from typing import Any, Sequence, TextIO


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
    def warntle(self) -> bool | None:
        return self.value[1]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Status) and self.id == other.id

    def __hash__(self) -> int:
        return super().__hash__()

    def set_warntle(self, state: bool | None = True) -> Status:
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
    colorful = False

    @staticmethod
    def setup(colorful: bool) -> None:
        Color.colorful: bool = colorful
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
    def colorize(status: Status, text: Any, end: Color | None = None) -> str:
        index = status in (Status.ok, Status.valid)
        return "%s%s%s" % (
            (Color.warning, Color.infog)[index],
            text,
            end or Color.normal,
        )


_sow = sys.stdout.write
_sew = sys.stderr.write

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

# {{{ ---------------------- messages ----------------------------


class Logger:
    def __init__(self, file: TextIO = sys.stderr):
        self.file = file

    def write(self, text: Any) -> None:
        self.file.write(text)

    def colored(self, text: Any, color: Color, end: Any = "\n") -> None:
        self.write("%s%s%s%s" % (color, text, Color.normal, end))

    def error(self, text: Any, *, doquit: bool = True) -> None:
        message = "%s%s%s\n" % (Color.error, text, Color.normal)
        self.write(message)
        if doquit:
            quit(1)

    def warning(self, text: Any) -> None:
        self.colored(text, Color.warning)

    # blue
    def infob(self, text: Any) -> None:
        self.colored(text, Color.infob)

    # green
    def infog(self, text: Any) -> None:
        self.colored(text, Color.infog)

    def info(self, text: Any) -> None:
        self.write(f"{text}\n")

    def plain(self, text: Any) -> None:
        self.write(text)


default_logger = Logger()


class BufferedLogger(Logger):
    def __init__(self, file: TextIO = sys.stderr):
        self.file = file
        self.buffer: list[str] = []
        self.open = True

    def error(self, text: Any, *, doquit: bool = True, flush: bool = True) -> None:
        message = "%s%s%s\n" % (Color.error, text, Color.normal)
        self.write(message)
        if flush:
            self.flush()
        if doquit:
            quit(1)

    def write(self, text: Any) -> None:
        self.buffer.append(text)

    def read(self) -> str:
        return "".join(self.buffer)

    def flush(self) -> None:
        self.file.write(self.read())
        self.buffer.clear()

    def close(self) -> None:
        self.open = False


class ParallelLoggerManager:
    def __init__(self):
        self.sinks: list[BufferedLogger] = []
        self.last_open = 0
        self.closed_event = threading.Event()

    def get_sink(self) -> BufferedLogger:
        self.sinks.append(BufferedLogger())
        return self.sinks[-1]

    def clear_buffers(self) -> None:
        for c in self.sinks:
            c.buffer.clear()

    def read_closed(self):
        res: list[str] = []
        while self.last_open < len(self.sinks):
            sink = self.sinks[self.last_open]
            if sink.open:
                break
            res.append(sink.read())
            self.last_open += 1
        return "".join(res)


def error(text: Any, doquit: bool = True) -> None:
    _sew("%s%s%s\n" % (Color.error, text, Color.normal))
    if doquit:
        quit(1)


def warning(text: Any) -> None:
    _sew("%s%s%s\n" % (Color.warning, text, Color.normal))


def infob(text: Any) -> None:
    _sew("%s%s%s\n" % (Color.infob, text, Color.normal))


def infog(text: Any) -> None:
    _sew("%s%s%s\n" % (Color.infog, text, Color.normal))


def info(text: Any) -> None:
    _sew(f"{text}\n")


def plain(text: Any) -> None:
    _sew(text)


# }}}


def wide_str(width: int, side: int) -> str:
    return "{:%s%ss}" % (("", ">", "<")[side], width)


def table_row(
    color: Color,
    columns: Sequence[Any],
    widths: Sequence[int],
    alignments: Sequence[int],
    header: bool = False,
):
    columns = list(columns)
    for i in range(len(columns)):
        if header == True:
            columns[i] = wide_str(widths[i], alignments[i]).format(columns[i])
        elif isinstance(columns[i], Status):
            status = columns[i]
            columns[i] = status.colored() + " " * (widths[i] - len(str(status)))
            columns[i] += str(Color.table)
        else:
            columns[i] = wide_str(widths[i], alignments[i]).format(str(columns[i]))
            columns[i] = str(color) + columns[i] + str(Color.table)
    return "%s| %s |%s" % (str(Color.table), " | ".join(columns), str(Color.normal))


def table_header(
    columns: Sequence[Any], widths: Sequence[int], alignments: Sequence[int]
):
    first_row = table_row(Color.table, columns, widths, alignments, True)
    second_row = "|".join(
        [str(Color.table)] + ["-" * (w + 2) for w in widths] + [str(Color.normal)]
    )
    return "\n%s\n%s" % (first_row, second_row)


def color_test() -> None:
    Color.setup(True)

    info("white")
    infob("blue")
    infog("green")
    warning("warning")
    error("error", doquit=False)
    _sew("".join([s.colored() for s in Status]) + "\n")
    for i in range(11):
        _sew("%s%s/%s%s\n" % (Color.score_color(i, 10), i, 10, Color.normal))
