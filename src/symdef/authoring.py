"""The author door: what a library's author uses to build, lint and keep a library (D84).

A consumer never calls these; it loads a library and draws from it through `symdef`.
"""

from symdef.files import stale_build, write_build
from symdef.lint import RULES, finding_key, lint
from symdef.model import LibraryConfig
from symdef.project import build, check, init

__all__ = [
    "RULES",
    "LibraryConfig",
    "build",
    "check",
    "finding_key",
    "init",
    "lint",
    "stale_build",
    "write_build",
]
