import re

import pytest

from symdef.units import (
    DEFAULT_GRID,
    DEFAULT_MODULE_MM,
    GRID_DIVISION,
    Grid,
    ceil_divisions,
    from_divisions,
    on_grid,
    snap,
    to_divisions,
)


def test_constants():
    assert DEFAULT_MODULE_MM == 2.5
    assert GRID_DIVISION == 0.125


def test_snap_rounds_to_nearest_eighth():
    assert snap(0.1) == 0.125
    assert snap(0.06) == 0.0
    assert snap(-0.3) == -0.25
    assert snap(1.0) == 1.0


def test_on_grid():
    assert on_grid(0.375)
    assert on_grid(-2.0)
    assert not on_grid(0.3)
    assert on_grid(0.3, tol=0.1)


COARSE = Grid(module_mm=5, divisions_per_module=4)


@pytest.mark.parametrize("grid", [DEFAULT_GRID, COARSE])
def test_divisions_round_trip(grid):
    for n in range(-16, 17):
        assert to_divisions(grid, from_divisions(grid, n)) == n


def test_to_divisions_of_a_negative_value():
    assert to_divisions(DEFAULT_GRID, -0.5) == -4


@pytest.mark.parametrize("v", [0.1, 0.3, float("nan"), float("inf")])
def test_off_grid_or_non_finite_values_raise(v):
    with pytest.raises(ValueError, match=re.escape(repr(v))):
        to_divisions(DEFAULT_GRID, v)


def test_ceil_divisions_on_an_exact_multiple():
    assert ceil_divisions(DEFAULT_GRID, 1.0) == 8


def test_ceil_divisions_just_above_a_multiple():
    assert ceil_divisions(DEFAULT_GRID, 1.0 + 0.01) == 9


def test_ceil_divisions_ignores_float_noise():
    assert ceil_divisions(DEFAULT_GRID, 1.0 + 1e-12) == 8
