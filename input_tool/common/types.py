from pathlib import Path
from typing import NewType

# Type aliases
RelativePath = Path
Directory = Path
ExecutableFile = Path
TempFile = Path

ShellCommand = NewType("ShellCommand", str)
