from pathlib import Path
from typing import NewType, TypeAlias

RelativePath: TypeAlias = Path
Directory: TypeAlias = Path
ExecutableFile: TypeAlias = Path
TempFile: TypeAlias = Path

ShellCommand = NewType("ShellCommand", str)
