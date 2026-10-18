"""A centred "grid" text sits at the box start edge plus width // 2 divisions (D96)."""

import pytest
from test_text_block import CAP_FONT, GRID, GRID_FONT, HEIGHT

from symdef import Centre, Direction, Point, Slot, slot_lines

START = 1.0  # modules: the box's start edge, on the grid
G = 1 / GRID.divisions_per_module


def render_centre(start_g, width_g):
    """Render's rule (`marker.width // 2`): an offset from the edge, in divisions."""
    return start_g + width_g // 2


def slot_of(width_g, *, turn=False, side=Centre.C):
    """A slot whose box starts at START and is `width_g` divisions long along the text."""
    length = width_g * G
    if turn:
        return Slot("s", Point(0.5, START + length / 2), side, (1.0, length), turn=True)
    return Slot("s", Point(START + length / 2, 0.5), side, (length, 1.0))


@pytest.mark.parametrize("width_g", [6, 7, 9])
def test_a_centred_text_sits_a_floored_half_width_from_the_edge(width_g):
    got = slot_lines(slot_of(width_g), "AB", HEIGHT, GRID_FONT, GRID)[0].point.x
    assert got / G == pytest.approx(render_centre(8, width_g))


@pytest.mark.parametrize("width_g", [6, 7])
def test_a_turned_centred_text_sits_there_along_the_height(width_g):
    got = slot_lines(slot_of(width_g, turn=True), "AB", HEIGHT, GRID_FONT, GRID)[0].point.y
    assert got / G == pytest.approx(render_centre(8, width_g))


def test_a_north_slot_text_is_centred_the_same_way():
    got = slot_lines(slot_of(7, side=Direction.N), "AB", HEIGHT, GRID_FONT, GRID)[0].point.x
    assert got / G == pytest.approx(render_centre(8, 7))


def test_cap_keeps_the_true_centre():
    got = slot_lines(slot_of(7), "AB", HEIGHT, CAP_FONT, GRID)[0].point.x
    assert got / G == pytest.approx(8 + 3.5)
