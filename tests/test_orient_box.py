"""`orient_box` turns a box about the origin as `orient` turns a symbol (D76)."""

import pytest

from symdef.boxes import body_box
from symdef.geometry import Box, Line, Orientation, Point, Polyline
from symdef.model import Reference, Status, Symbol, SymbolKind
from symdef.orient import orient, orient_box


def lopsided():
    """A non-square body away from the origin, so a lost mirror or turn moves the box."""
    return Symbol(
        "t",
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", "1"),
        (Line(Point(1, 2), Point(5, 2)), Polyline((Point(2, -1), Point(2, 3)))),
    )


@pytest.mark.parametrize("orientation", list(Orientation))
def test_orienting_the_body_box_is_the_body_box_of_the_oriented_symbol(orientation):
    symbol = lopsided()
    assert orient_box(body_box(symbol), orientation) == body_box(orient(symbol, orientation))


def test_a_mirror_flips_x_and_a_quarter_turn_swaps_the_extents():
    box = Box(Point(1, 2), Point(5, 3))
    assert orient_box(box, Orientation.MR0) == Box(Point(-5, 2), Point(-1, 3))
    assert orient_box(box, Orientation.R90) == Box(Point(-3, 1), Point(-2, 5))
    assert orient_box(box, Orientation.R0) == box


# Written by hand for Box((1, 2), (5, 3)). A quarter turn is clockwise on screen, (x, y) -> (-y, x);
# a mirror flips x first and the turn follows: MR90 is (x, y) -> (-x, y) -> (-y, -x).
HAND_BOXES = {
    Orientation.R0: Box(Point(1, 2), Point(5, 3)),
    Orientation.R90: Box(Point(-3, 1), Point(-2, 5)),
    Orientation.R180: Box(Point(-5, -3), Point(-1, -2)),
    Orientation.R270: Box(Point(2, -5), Point(3, -1)),
    Orientation.MR0: Box(Point(-5, 2), Point(-1, 3)),
    Orientation.MR90: Box(Point(-3, -5), Point(-2, -1)),
    Orientation.MR180: Box(Point(1, -3), Point(5, -2)),
    Orientation.MR270: Box(Point(2, 1), Point(3, 5)),
}


@pytest.mark.parametrize("orientation", list(Orientation))
def test_all_eight_orientations_give_the_hand_written_box(orientation):
    box = Box(Point(1, 2), Point(5, 3))
    assert orient_box(box, orientation) == HAND_BOXES[orientation]
