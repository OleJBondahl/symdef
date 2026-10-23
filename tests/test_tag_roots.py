"""`tag_roots`: the text root of a tag slot and its reflections, in grid divisions (D113)."""

from dataclasses import astuple, replace

import pytest
from test_font import FONT

from symdef import TextRoot, tag_roots
from symdef.errors import InvalidValueError, UnknownNameError
from symdef.geometry import Direction, Line, Orientation, Point
from symdef.gridmeasure import measure
from symdef.model import Library, Port, Reference, Slot, Status, Symbol, SymbolKind
from symdef.units import Grid

# One division is one module, so a module-unit coordinate is its division.
ONE = Library(
    "S", "S", "", {}, font=FONT, grid=Grid(divisions_per_module=1, wire_pitch=1, wire_pitch_fine=1)
)
HEIGHT = 2  # cap height 1.4 with FONT


def box(x0, y0, x1, y1):
    corners = [Point(x0, y0), Point(x1, y0), Point(x1, y1), Point(x0, y1)]
    return tuple(Line(a, b) for a, b in zip(corners, [*corners[1:], corners[0]], strict=True))


def build(name, elements, slots, ports=(), pole_pitch=None):
    return Symbol(
        name,
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", "1"),
        elements,
        ports=ports,
        slots=slots,
        pole_pitch=pole_pitch,
    )


def marking(side=Direction.N, at=(0, 3)):
    return Slot("marking.1", Point(*at), side, (1, 1))


TAG = Slot("tag", Point(3, 8), Direction.E, (1, 1))
TOP_PIN = Port("1", Point(0, 4), Direction.N)
# The spec's worked example: body x -2..2, y 4..12, a top pin at x 0, a marking slot bottom at 3.
MAKE = build("make", box(-2, 4, 2, 12), (TAG, marking()), (TOP_PIN,))
SIDEWAYS = build("side", box(-2, 4, 2, 12), (TAG,), (Port("1", Point(0, 12), Direction.S),))
INSIDE = build("in", box(0, 0, 8, 8), (Slot("tag", Point(1, 1), Direction.E, (2, 1)),))
LOW_MARK = build("low", box(-2, 4, 2, 12), (TAG, marking(Direction.S, (0, 5))), (TOP_PIN,))
ALL = [MAKE, SIDEWAYS, LOW_MARK]


def roots(symbol, gap=0.5, orientation=Orientation.R0, library=ONE):
    return tag_roots(symbol, orientation, library, gap=gap, marking_height=HEIGHT)


def test_the_worked_example():
    assert roots(MAKE) == (
        TextRoot(-2, 3, "right", "baseline"),
        TextRoot(-2, 13, "right", "top"),
        TextRoot(2, 3, "left", "baseline"),
        TextRoot(2, 13, "left", "top"),
    )


@pytest.mark.parametrize("orientation", list(Orientation))
@pytest.mark.parametrize("symbol", ALL, ids=lambda s: s.name)
def test_each_mirror_reflects_the_first_through_the_body_centre(symbol, orientation):
    tl, bl, tr, br = roots(symbol, orientation=orientation)
    body = measure(symbol, orientation, ONE).body
    sx, sy = body.min.x + body.max.x, body.min.y + body.max.y
    other = {"left": "right", "right": "left", "baseline": "top", "top": "baseline"}
    assert astuple(bl) == (tl.x, sy - tl.y, tl.h, other[tl.v])
    assert astuple(tr) == (sx - tl.x, tl.y, other[tl.h], tl.v)
    assert astuple(br) == (sx - tl.x, sy - tl.y, other[tl.h], other[tl.v])


def test_the_marking_baseline_comes_from_slot_text():
    # Side S: the baseline sits one cap height (1.4) below the point 5, rounded to 6.
    assert roots(LOW_MARK, gap=1)[0] == TextRoot(-4, 6, "right", "baseline")


def test_a_root_inside_the_body_is_lifted_to_the_top_edge():
    # (-2, 6) lies within the body's x range and below its top edge 4: lifted to 4.
    assert roots(LOW_MARK)[0] == TextRoot(-2, 4, "right", "baseline")


def test_a_baseline_above_the_body_is_not_lifted():
    assert roots(MAKE)[0].y == 3


def test_a_sideways_view_hangs_from_the_top_left_corner():
    tl = roots(SIDEWAYS)[0]
    assert tl == TextRoot(-2, 4 - 2, "left", "baseline")


def test_a_tag_slot_inside_the_body_gives_its_own_root_four_times():
    # Side E, box x 1..3, y 0.5..1.5 rounded out to 0..2; the baseline is 1 + 0.5 * 1.4 = 1.7 -> 2.
    own = TextRoot(1, 2, "left", "baseline")
    assert roots(INSIDE) == (own, own, own, own)


def test_a_west_tag_slot_inside_the_body_starts_at_its_right_edge():
    west = replace(INSIDE, slots=(Slot("tag", Point(4, 4), Direction.W, (2, 1)),))
    own = TextRoot(4, 5, "right", "baseline")
    assert roots(west) == (own, own, own, own)


def test_a_repeated_symbol_doubles_the_gap():
    wide = replace(MAKE, pole_pitch=8)
    assert roots(wide)[0].x == -4  # port x 0, gap 0.5 * 8 = 4 divisions


def test_a_top_port_with_no_marking_slot_sits_on_the_top_edge():
    bare = replace(MAKE, slots=(TAG,))
    assert roots(bare)[0] == TextRoot(-2, 4, "right", "baseline")


def test_the_gap_rounds_to_the_nearest_division_halves_up():
    # 0.625 * 4 = 2.5 divisions: half up gives 3 (to-even would give 2).
    assert roots(MAKE, gap=0.625)[0].x == -3


def test_a_symbol_with_no_tag_slot_is_refused_by_name():
    with pytest.raises(UnknownNameError, match="'make'"):
        roots(replace(MAKE, slots=(marking(),)))


def test_a_negative_gap_is_refused():
    with pytest.raises(InvalidValueError, match="gap"):
        roots(MAKE, gap=-0.5)


def test_a_marking_height_above_zero_is_needed():
    with pytest.raises(InvalidValueError, match="marking_height"):
        tag_roots(MAKE, Orientation.R0, ONE, gap=0.5, marking_height=0)
