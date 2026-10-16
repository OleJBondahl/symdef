import pytest

from symdef.errors import InvalidValueError
from symdef.geometry import Direction
from symdef.gridtypes import GridBox, GridPoint, GridPort


def test_union_of_one_box_gives_that_box():
    box = GridBox(GridPoint(1, 2), GridPoint(3, 4))
    assert GridBox.union(box) == box


def test_union_of_three_boxes_is_exact():
    boxes = (
        GridBox(GridPoint(0, 0), GridPoint(4, 2)),
        GridBox(GridPoint(-2, 1), GridPoint(3, 5)),
        GridBox(GridPoint(1, -3), GridPoint(2, 1)),
    )
    assert GridBox.union(*boxes) == GridBox(GridPoint(-2, -3), GridPoint(4, 5))


def test_union_of_no_box_raises():
    with pytest.raises(InvalidValueError, match=r"union needs at least one box"):
        GridBox.union()


def test_width_and_height_are_ints():
    box = GridBox(GridPoint(-2, -3), GridPoint(4, 5))
    assert box.width == 6
    assert box.height == 8
    assert isinstance(box.width, int)
    assert isinstance(box.height, int)


def test_grid_point_rejects_a_float_and_names_the_value():
    with pytest.raises(InvalidValueError, match=r"GridPoint\.x is 1\.5;"):
        GridPoint(1.5, 0)


def test_grid_port_rejects_a_float_and_names_the_value():
    with pytest.raises(InvalidValueError, match=r"GridPort\.y is 2\.0;"):
        GridPort("1", 0, 2.0, Direction.N)


def test_grid_point_rejects_bool():
    with pytest.raises(InvalidValueError, match=r"GridPoint\.y is True;"):
        GridPoint(0, y=True)


def test_the_message_says_how_to_fix_it():
    with pytest.raises(
        InvalidValueError,
        match=r"grid divisions are whole numbers; round with ceil_divisions or to_divisions",
    ):
        GridPoint(0.5, 0)
