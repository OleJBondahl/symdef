"""`reference_cell` and `floor_divisions` (D129)."""

import math

import pytest

from symdef.errors import InvalidValueError, ReferenceCellError
from symdef.gridtypes import GridPoint
from symdef.refgrid import reference_cell
from symdef.units import DEFAULT_GRID, Grid, floor_divisions

COLUMNS = ("A", "B", "C", "D", "E", "F")
ROWS = ("1", "2", "3", "4")
WIDTH, HEIGHT = 60, 40  # cells are 10 divisions each way


def cell(x, y):
    return reference_cell(COLUMNS, ROWS, WIDTH, HEIGHT, GridPoint(x, y))


@pytest.mark.parametrize("k", range(len(COLUMNS)))
def test_every_column_label_at_both_ends_of_its_cell(k):
    assert cell(10 * k, 0)[0] == COLUMNS[k]
    assert cell(10 * k + 9, 0)[0] == COLUMNS[k]


@pytest.mark.parametrize("k", range(len(ROWS)))
def test_every_row_label_at_both_ends_of_its_cell(k):
    assert cell(0, 10 * k)[1] == ROWS[k]
    assert cell(0, 10 * k + 9)[1] == ROWS[k]


def test_corners_and_the_far_edge():
    assert cell(0, 0) == ("A", "1")
    assert cell(WIDTH, 0) == ("F", "1")
    assert cell(0, HEIGHT) == ("A", "4")
    assert cell(WIDTH, HEIGHT) == ("F", "4")


def test_a_shared_edge_belongs_to_the_max_side_cell():
    assert cell(10, 10) == ("B", "2")


def test_uneven_extent_divides_by_the_count_not_a_rounded_cell_size():
    assert reference_cell(("a", "b", "c"), ("x",), 10, 5, GridPoint(6, 0)) == ("b", "x")
    assert reference_cell(("a", "b", "c"), ("x",), 10, 5, GridPoint(7, 0)) == ("c", "x")


@pytest.mark.parametrize(("x", "y"), [(-1, 0), (0, -1), (WIDTH + 1, 0), (0, HEIGHT + 1)])
def test_a_point_outside_the_grid_raises_naming_the_point_and_the_grid(x, y):
    with pytest.raises(ReferenceCellError, match=rf"\({x}, {y}\).*6 columns by 4 rows.*60 by 40"):
        cell(x, y)


def test_the_outside_error_is_an_invalid_value_error():
    assert issubclass(ReferenceCellError, InvalidValueError)


@pytest.mark.parametrize(
    ("columns", "rows", "width", "height", "match"),
    [
        ((), ROWS, WIDTH, HEIGHT, "at least one column label"),
        (COLUMNS, (), WIDTH, HEIGHT, "at least one column label"),
        (COLUMNS, ROWS, 0, HEIGHT, "0 by 40 divisions"),
        (COLUMNS, ROWS, WIDTH, 0, "60 by 0 divisions"),
    ],
)
def test_an_unusable_grid_is_refused(columns, rows, width, height, match):
    with pytest.raises(InvalidValueError, match=match):
        reference_cell(columns, rows, width, height, GridPoint(0, 0))


def test_floor_divisions_rounds_down():
    # 2.5 mm module, 8 divisions: one division is 0.3125 mm.
    assert floor_divisions(DEFAULT_GRID, 0) == 0
    assert floor_divisions(DEFAULT_GRID, 0.3125) == 1  # on grid
    assert floor_divisions(DEFAULT_GRID, 2.5) == 8  # on grid
    assert floor_divisions(DEFAULT_GRID, 0.3124999999999) == 1  # float noise below a division
    assert floor_divisions(DEFAULT_GRID, 0.62) == 1  # off grid, just under two
    assert floor_divisions(DEFAULT_GRID, 0.32) == 1  # off grid, just over one
    assert floor_divisions(Grid(module_mm=5.0, divisions_per_module=4), 1.3) == 1


@pytest.mark.parametrize("bad", [-0.1, math.inf, math.nan])
def test_floor_divisions_refuses_a_floor_that_is_not_a_length(bad):
    with pytest.raises(InvalidValueError, match="not a length"):
        floor_divisions(DEFAULT_GRID, bad)
