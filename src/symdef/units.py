"""Module unit and grid constants, the `Grid` a library declares, and snapping to the grid."""

import math
from dataclasses import dataclass

DEFAULT_MODULE_MM: float = 2.5
GRID_DIVISION: float = 0.125
DEFAULT_DIVISIONS_PER_MODULE: int = 8


@dataclass(frozen=True, slots=True)
class Grid:
    """The drawing grid of a library: the size of the module and how many divisions it has.

    Attributes:
        module_mm: One module in millimetres.
        divisions_per_module: How many grid divisions make one module; a power of two, so a
            division is exact in floating point.
    """

    module_mm: float = DEFAULT_MODULE_MM
    divisions_per_module: int = DEFAULT_DIVISIONS_PER_MODULE

    @property
    def division(self) -> float:
        """One grid division in module units."""
        return 1 / self.divisions_per_module


DEFAULT_GRID = Grid()


def snap(v: float) -> float:
    """Round a value in module units to the nearest grid division (`GRID_DIVISION`, 0.125 M)."""
    return round(v / GRID_DIVISION) * GRID_DIVISION


def on_grid(v: float, tol: float = 1e-9) -> bool:
    """Return whether a value in module units is within `tol` of a grid division."""
    return abs(v - snap(v)) <= tol


_DIVISION_TOLERANCE: float = 1e-9


def to_divisions(grid: Grid, v: float) -> int:
    """Return how many grid divisions a value in module units spans; the value must sit on the grid.

    Off-grid values raise, so a drawing never gets a half division by accident.
    """
    n = v * grid.divisions_per_module
    if not math.isfinite(n) or abs(n - round(n)) > _DIVISION_TOLERANCE:
        msg = f"{v!r} is not on the grid of {grid.divisions_per_module} divisions per module"
        raise ValueError(msg)
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
