from typing import TypeVar

# create subtype of str
Path = TypeVar("Path", str, os.PathLike)
ProgramName = TypeVar("ProgramName", Path)
