"""Module unit and grid constants, the `Grid` a library declares, and snapping to the grid."""

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
