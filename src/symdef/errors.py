"""Domain errors."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from symdef.model import Finding


class SymdefError(Exception):
    """Base class for every error this package raises."""


class InvalidValueError(SymdefError):
    """An argument or data is unusable; the message names the value, what is valid and the fix."""


class ReferenceCellError(InvalidValueError):
    """A point lies outside the reference grid of a page frame; the message names both."""


class UnknownNameError(SymdefError):
    """A name is not in the set it was looked up in; the message lists the valid names."""


class UnknownSymbolError(SymdefError):
    """A library lookup found no symbol with the requested reference number."""


class LibraryError(SymdefError):
    """A library failed to load; `findings` says why."""

    def __init__(self, findings: tuple[Finding, ...]) -> None:
        """Keep the findings and summarise them in the message."""
        super().__init__("; ".join(f"{f.rule}: {f.message}" for f in findings))
        self.findings = findings
