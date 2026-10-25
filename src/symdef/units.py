"""Module unit and grid constants, the `Grid` a library declares, and snapping to the grid."""

import math
from dataclasses import dataclass

from symdef.errors import InvalidValueError

DEFAULT_MODULE_MM: float = 2.5
GRID_DIVISION: float = 0.125
DEFAULT_DIVISIONS_PER_MODULE: int = 8
DEFAULT_WIRE_PITCH: int = 8
DEFAULT_WIRE_PITCH_FINE: int = 4


def module_error(value: object) -> str | None:
    """Return why `value` is not a usable `module_mm`, or None; `Grid` and the loader share it."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return f"module_mm {value!r} is not a number; give a number of millimetres above zero"
    if not math.isfinite(value) or value <= 0:
        return (
            f"module_mm {value!r} is not above zero; give a finite number of millimetres above zero"
        )
    return None


def divisions_error(value: object) -> str | None:
    """Return why `value` is not a usable `divisions_per_module`, or None."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value & (value - 1):
        return (
            f"divisions_per_module {value!r} is not a power of two; "
            "use 1, 2, 4, 8, 16 and so on, so a division is exact in floating point"
        )
    return None


def pitch_error(standard: object, fine: object) -> str | None:
    """Return why `standard` and `fine` are not usable wire pitches, in divisions, or None."""
    for name, value in (("wire_pitch", standard), ("wire_pitch_fine", fine)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            return f"{name} {value!r} is not a whole number of divisions above zero; use 1 or more"
    if standard % fine:  # ty: ignore[unsupported-operator] - both proved whole numbers above
        return (
            f"wire_pitch_fine {fine!r} does not divide wire_pitch {standard!r}; "
            "give a fine pitch that divides the standard one"
        )
    return None


def margin_error(value: object) -> str | None:
    """Return why `value` is not a usable `outline_margin`, or None."""
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        return f"outline_margin {value!r} is not a whole number of divisions; use 0 or more"
    return None


STRETCH_SPLITS = ("weight", "whole")


def split_error(value: object) -> str | None:
    """Return why `value` is not a `stretch_split`, or None."""
    if value in STRETCH_SPLITS:
        return None
    return f'stretch_split {value!r} is not one of {STRETCH_SPLITS}; use "weight" or "whole"'


@dataclass(frozen=True, slots=True)
class Grid:
    """The drawing grid of a library: the size of the module and how many divisions it has.

    Attributes:
        module_mm: One module in millimetres.
        divisions_per_module: How many grid divisions make one module; a power of two, so a
            division is exact in floating point.
        wire_pitch: The standard wire pitch in divisions; every port sits on it.
        wire_pitch_fine: The fine wire pitch in divisions, for a dense page; it divides
            `wire_pitch`. A library has these two pitches and no third.
        stretch_split: How `stretch` shares a growth among several cuts: "weight" (by weight, the
            default) or "whole" (in whole divisions, near cuts floored; D97).
        declared_outline_margin: How far, in divisions, a unit outline stands off the boxes it
            encloses, on all four sides, or None when the library declares none (D120). Read the
            margin through `outline_margin`, which raises when none is declared.
    """

    module_mm: float = DEFAULT_MODULE_MM
    divisions_per_module: int = DEFAULT_DIVISIONS_PER_MODULE
    wire_pitch: int = DEFAULT_WIRE_PITCH
    wire_pitch_fine: int = DEFAULT_WIRE_PITCH_FINE
    stretch_split: str = "weight"
    declared_outline_margin: int | None = None

    def __post_init__(self) -> None:
        """Raise `InvalidValueError` naming the value and fix, for a bad grid value."""
        error = (
            module_error(self.module_mm)
            or divisions_error(self.divisions_per_module)
            or pitch_error(self.wire_pitch, self.wire_pitch_fine)
            or split_error(self.stretch_split)
            or margin_error(self.declared_outline_margin)
        )
        if error:
            raise InvalidValueError(error)

    @property
    def outline_margin(self) -> int:
        """Return the unit outline's margin in divisions; raise when the library declares none."""
        if self.declared_outline_margin is None:
            msg = (
                "this library declares no outline_margin; add `outline_margin = <divisions>` "
                "under [grid] in library.toml (D120)"
            )
            raise InvalidValueError(msg)
        return self.declared_outline_margin

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


def floor_divisions(grid: Grid, floor_mm: float) -> int:
    """Return the smallest whole number of grid divisions that holds a length floor in millimetres.

    It rounds as `ceil_divisions` does, so a floor on a division counts as that division.

    Raises:
        InvalidValueError: `floor_mm` is negative or not finite.
    """
    if not math.isfinite(floor_mm) or floor_mm < 0:
        msg = f"floor {floor_mm!r} is not a length; give a finite number of millimetres, 0 or more"
        raise InvalidValueError(msg)
    return ceil_divisions(grid, floor_mm / grid.module_mm)
