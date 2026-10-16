"""Module unit and grid constants, the `Grid` a library declares, and snapping to the grid."""

import math
from dataclasses import dataclass

from symdef.errors import InvalidValueError

DEFAULT_MODULE_MM: float = 2.5
GRID_DIVISION: float = 0.125
DEFAULT_DIVISIONS_PER_MODULE: int = 8


def divisions_error(value: object) -> str | None:
    """Return why `value` is not a usable `divisions_per_module`, or None."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value & (value - 1):
        return (
            f"divisions_per_module {value!r} is not a power of two; "
            "use 1, 2, 4, 8, 16 and so on, so a division is exact in floating point"
        )
    return None


@dataclass(frozen=True, slots=True)
class Grid:
    """The drawing grid of a library: how many divisions make one module.

    The size of a module in millimetres is the sheet's, never the library's; a call that needs
    millimetres takes `module_mm` as an argument.

    Attributes:
        divisions_per_module: How many grid divisions make one module; a power of two, so a
            division is exact in floating point.
    """

    divisions_per_module: int = DEFAULT_DIVISIONS_PER_MODULE

    def __post_init__(self) -> None:
        """Raise `InvalidValueError` naming the value and fix, for unusable divisions."""
        error = divisions_error(self.divisions_per_module)
        if error:
            raise InvalidValueError(error)

    @property
    def division(self) -> float:
        """One grid division in module units."""
        return 1 / self.divisions_per_module


DEFAULT_GRID = Grid()


def snap(v: float, grid: Grid = DEFAULT_GRID) -> float:
    """Round a value in module units to the nearest division of `grid`.

    With no grid it is the default grid, `GRID_DIVISION` (0.125 M), so a call without one gives
    the output it always gave.
    """
    return round(v / grid.division) * grid.division


def on_grid(v: float, tol: float = 1e-9, grid: Grid = DEFAULT_GRID) -> bool:
    """Return whether a value in module units is within `tol` of a division of `grid`.

    With no grid it is the default grid, as for `snap`.
    """
    return abs(v - snap(v, grid)) <= tol


_DIVISION_TOLERANCE: float = 1e-9


def to_divisions(grid: Grid, v: float) -> int:
    """Return how many grid divisions a value in module units spans; the value must sit on the grid.

    Off-grid values raise, so a drawing never gets a half division by accident.
    """
    n = v * grid.divisions_per_module
    if not math.isfinite(n) or abs(n - round(n)) > _DIVISION_TOLERANCE:
        msg = f"{v!r} is not on the grid of {grid.divisions_per_module} divisions per module"
        raise InvalidValueError(msg)
    return round(n)


def from_divisions(grid: Grid, n: int) -> float:
    """Return the value in module units of `n` grid divisions."""
    return n / grid.divisions_per_module


def ceil_divisions(grid: Grid, v: float) -> int:
    """Round a value in module units up to whole grid divisions.

    A value within the tolerance above a multiple counts as that multiple, so float noise
    does not add a division.
    """
    return math.ceil(v * grid.divisions_per_module - _DIVISION_TOLERANCE)
