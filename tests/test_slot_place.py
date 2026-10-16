"""`slot_text` and `slot_box`: where a slot's string sits and the room it takes (D74)."""

import pytest
from test_font import FONT

from symdef.boxes import slot_box
from symdef.geometry import Box, Direction, Point
from symdef.model import Centre, Slot
from symdef.slottext import SIDE_ALIGN, TURNED_ALIGN, TextPlacement, slot_text

HEIGHT = 2  # with FONT the cap height is 1.4 and "ABi" is 2.9 wide


def slot(side, *, turn=False):
    return Slot("tag", Point(3, 4), side, (2, 1), turn)


def placed(side, *, turn, font=FONT):
    result = slot_text(slot(side, turn=turn), "ABi", HEIGHT, font)
    return result.point.x, result.point.y, result.anchor, result.turned


def approx_box(box):
    return (box.min.x, box.min.y, box.max.x, box.max.y)


UPRIGHT = {
    Direction.E: (3, 4.7, "start"),
    Direction.W: (3, 4.7, "end"),
    Direction.N: (3, 4, "middle"),
    Direction.S: (3, 5.4, "middle"),
    Centre.C: (3, 4.7, "middle"),
}
TURNED = {
    Direction.N: (3.7, 4, "start"),
    Direction.S: (3.7, 4, "end"),
    Direction.E: (4.4, 4, "middle"),
    Direction.W: (3, 4, "middle"),
    Centre.C: (3.7, 4, "middle"),
}


@pytest.mark.parametrize("side", UPRIGHT)
def test_an_upright_slot_text_sits_by_its_side(side):
    x, y, anchor, turned = placed(side, turn=False)
    assert (x, y) == pytest.approx(UPRIGHT[side][:2])
    assert (anchor, turned) == (UPRIGHT[side][2], False)


@pytest.mark.parametrize("side", TURNED)
def test_a_turned_slot_text_sits_by_its_side(side):
    x, y, anchor, turned = placed(side, turn=True)
    assert (x, y) == pytest.approx(TURNED[side][:2])
    assert (anchor, turned) == (TURNED[side][2], True)


def test_with_no_font_the_cap_height_is_072_em():
    x, y, _, _ = placed(Direction.S, turn=False, font=None)
    assert (x, y) == pytest.approx((3, 4 + 0.72 * HEIGHT))


def test_the_placement_is_a_value():
    assert slot_text(slot(Direction.N), "x", 1, None) == TextPlacement(
        Point(3, 4), "middle", turned=False
    )


def test_the_tables_cover_every_side():
    assert set(SIDE_ALIGN) == set(TURNED_ALIGN) == {*Direction, Centre.C}


def test_a_slot_box_with_no_text_is_the_reserved_box():
    assert slot_box(slot(Direction.E)) == Box(Point(3, 3.5), Point(5, 4.5))
    assert slot_box(slot(Direction.W)) == Box(Point(1, 3.5), Point(3, 4.5))
    assert slot_box(slot(Direction.N)) == Box(Point(2, 3), Point(4, 4))
    assert slot_box(slot(Direction.S)) == Box(Point(2, 4), Point(4, 5))
    assert slot_box(slot(Centre.C)) == Box(Point(2, 3.5), Point(4, 4.5))


def test_a_slot_box_grows_by_the_measured_width():
    east = slot_box(slot(Direction.E), "ABi", HEIGHT, FONT)
    assert approx_box(east) == pytest.approx((3, 3.3, 5.9, 4.7))
    assert east.width == pytest.approx(2.9)
    west = slot_box(slot(Direction.W), "ABi", HEIGHT, FONT)
    assert approx_box(west) == pytest.approx((0.1, 3.3, 3, 4.7))
    north = slot_box(slot(Direction.N), "ABi", HEIGHT, FONT)
    assert approx_box(north) == pytest.approx((1.55, 2.6, 4.45, 4))


def test_a_turned_slot_box_grows_along_its_height():
    east = slot_box(slot(Direction.E, turn=True), "ABi", HEIGHT, FONT)
    assert approx_box(east) == pytest.approx((3, 2.55, 5, 5.45))
    north = slot_box(slot(Direction.N, turn=True), "ABi", HEIGHT, FONT)
    assert approx_box(north) == pytest.approx((2, 1.1, 4, 4))
    south = slot_box(slot(Direction.S, turn=True), "ABi", HEIGHT, FONT)
    assert approx_box(south) == pytest.approx((2, 4, 4, 6.9))


def test_a_text_that_fits_leaves_the_box_as_reserved():
    assert slot_box(slot(Direction.E), "i", 0.4, FONT) == slot_box(slot(Direction.E))


def test_a_text_with_no_font_is_measured_at_six_tenths_of_an_em():
    box = slot_box(slot(Direction.E), "abcde", HEIGHT)
    assert box.width == pytest.approx(0.6 * HEIGHT * 5)


def test_a_text_needs_a_height():
    with pytest.raises(ValueError, match="needs a height"):
        slot_box(slot(Direction.E), "ABi")
