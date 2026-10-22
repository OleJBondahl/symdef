"""`measure`: a symbol in whole grid divisions, extents rounded outward, ports exact (D82)."""

import math
from dataclasses import replace

import pytest
from test_font import FONT

from symdef.boxes import body_box, keepout_box, slot_box
from symdef.errors import InvalidValueError, UnknownNameError
from symdef.geometry import Box, Direction, Line, Point, Polyline, Text, Weight
from symdef.gridmeasure import Measure, measure
from symdef.gridtypes import GridBox, GridPoint, GridPort
from symdef.model import Library, Port, Reference, Slot, Status, Stretch, Symbol, SymbolKind
from symdef.orient import Orientation, orient
from symdef.stretch import stretch
from symdef.table import table
from symdef.units import Grid

HEIGHT = 2  # with FONT "ABiAB" is 5.0 wide


def build(*elements, slots=(), ports=()):
    return Symbol(
        "m",
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", "1"),
        elements,
        ports=ports,
        slots=slots,
    )


# Wider than tall, text of an off-grid width, a text slot, and ports on whole modules.
WIDE = build(
    Line(Point(0, 0), Point(6, 0)),
    Line(Point(0, 0), Point(0, 2)),
    Text("Bi", Point(3, 1), 1),
    slots=(Slot("tag", Point(6, 1), Direction.E, (1.5, 1)),),
    ports=(Port("a", Point(0, 2), Direction.S), Port("b", Point(6, 0), Direction.E)),
)
# Every extent on the quarter module, no text: the grid 4 per module halves each value of grid 8.
QUARTERS = build(
    Line(Point(-0.75, -0.25), Point(2.25, 1.5)),
    slots=(Slot("tag", Point(2.25, 0.5), Direction.E, (1.5, 0.5)),),
    ports=(Port("a", Point(0, 1), Direction.S),),
)
EIGHT = Library("S", "S", "", {}, font=FONT, grid=Grid(divisions_per_module=8))
FOUR = replace(EIGHT, grid=Grid(divisions_per_module=4))


def up(v, n):
    """Round `v` modules up to whole divisions, independent of symdef's own helper."""
    return math.ceil(round(v * n, 6))


def grid_box(box, n):
    """Return a module-unit box as a GridBox with the min rounded down and the max up."""
    return GridBox(
        GridPoint(-up(-box.min.x, n), -up(-box.min.y, n)),
        GridPoint(up(box.max.x, n), up(box.max.y, n)),
    )


@pytest.mark.parametrize("orientation", list(Orientation))
def test_measure_is_orient_then_the_boxes_divided_and_rounded_up(orientation):
    texts = {"tag": "ABiAB"}
    turned = orient(WIDE, orientation)
    result = measure(WIDE, orientation, EIGHT, texts, HEIGHT)
    slot = turned.slots[0]
    assert result.body == grid_box(body_box(turned, FONT), 8)
    assert result.slots == {"tag": grid_box(slot_box(slot, "ABiAB", HEIGHT, FONT), 8)}
    assert result.keepout == GridBox.union(result.body, *result.slots.values())
    assert result.ports == {
        p.id: GridPort(p.id, round(p.position.x * 8), round(p.position.y * 8), p.direction)
        for p in turned.ports
    }


def test_the_text_widens_the_slot_beyond_the_reserved_box():
    plain = measure(WIDE, Orientation.R0, EIGHT)
    texted = measure(WIDE, Orientation.R0, EIGHT, {"tag": "ABiAB"}, HEIGHT)
    assert (
        texted.slots["tag"].width == 43
    )  # 5.3 modules of text from the slot point, max rounded up
    assert plain.slots["tag"].width == 12


@pytest.mark.parametrize("orientation", list(Orientation))
def test_four_divisions_per_module_halves_every_value(orientation):
    fine = measure(QUARTERS, orientation, EIGHT)
    coarse = measure(QUARTERS, orientation, FOUR)

    def half(box):
        return GridBox(
            GridPoint(box.min.x // 2, box.min.y // 2), GridPoint(box.max.x // 2, box.max.y // 2)
        )

    assert half(fine.body) == coarse.body
    assert half(fine.keepout) == coarse.keepout
    assert {k: half(v) for k, v in fine.slots.items()} == coarse.slots
    assert {k: (v.x // 2, v.y // 2) for k, v in fine.ports.items()} == {
        k: (v.x, v.y) for k, v in coarse.ports.items()
    }


def test_a_negative_min_rounds_outward_not_toward_zero():
    off = build(Line(Point(-0.3, -0.3), Point(0.3, 0.3)))
    assert measure(off, Orientation.R0, EIGHT).body == GridBox(GridPoint(-3, -3), GridPoint(3, 3))


def test_a_port_off_the_grid_raises_naming_the_value():
    off = replace(WIDE, ports=(Port("a", Point(0.3, 2), Direction.S),))
    with pytest.raises(InvalidValueError, match=r"port 'a'.*0\.3"):
        measure(off, Orientation.R0, EIGHT)


def test_with_no_texts_a_slot_is_its_reserved_box():
    result = measure(WIDE, Orientation.R0, EIGHT)
    assert result.slots["tag"] == grid_box(slot_box(WIDE.slots[0]), 8)
    united = Box.union(keepout_box(WIDE, FONT), slot_box(WIDE.slots[0]))
    assert result.keepout == grid_box(united, 8)


def test_texts_need_a_height_and_a_slot_to_name():
    with pytest.raises(InvalidValueError, match="text_height"):
        measure(WIDE, Orientation.R0, EIGHT, {"tag": "A"})
    with pytest.raises(UnknownNameError, match="nope"):
        measure(WIDE, Orientation.R0, EIGHT, {"nope": "A"}, HEIGHT)


def test_a_bold_text_is_measured_with_the_bold_table():
    regular = build(Text("AB", Point(0, 0), 2, Weight.NORMAL))
    bold = build(Text("AB", Point(0, 0), 2, Weight.THICK))
    narrow = measure(regular, Orientation.R0, EIGHT).body
    wide = measure(bold, Orientation.R0, EIGHT).body
    assert (narrow.width, wide.width) == (up(2.4, 8), up(2.74, 8))


def test_the_value_is_read_only_and_a_library_with_no_font_still_measures():
    result = measure(WIDE, Orientation.R0, replace(EIGHT, font=None))
    assert isinstance(result, Measure)
    with pytest.raises(TypeError):
        result.slots["x"] = result.body  # ty: ignore[invalid-assignment]  # frozen on purpose
    with pytest.raises(TypeError):
        result.ports["x"] = None  # ty: ignore[invalid-assignment]  # frozen on purpose


COIL = build(
    Line(Point(0, 0), Point(4, 0)),
    Line(Point(0, 0), Point(0, 2)),
    slots=(Slot("table", Point(4, 1), Direction.S, (1, 1)),),
)
ROW = build(Line(Point(0, 0), Point(2, 1)))


# The attached 2 x 2 keep-out hangs on the turned slot's side, as a slot's reserved box does.
# Slot point and turned side per view, from orient(COIL): R0 (4, 1) S; R90 (-1, 4) W;
# R180 (-4, -1) N; R270 (1, -4) E. Boxes are by hand in 1/8 divisions.
ATTACHED_SLOT_BOX = {
    Orientation.R0: GridBox(GridPoint(24, 8), GridPoint(40, 24)),  # S: x 3..5, y 1..3
    Orientation.R90: GridBox(GridPoint(-24, 24), GridPoint(-8, 40)),  # W: x -3..-1, y 3..5
    Orientation.R180: GridBox(GridPoint(-40, -24), GridPoint(-24, -8)),  # N: x -5..-3, y -3..-1
    Orientation.R270: GridBox(GridPoint(8, -40), GridPoint(24, -24)),  # E: x 1..3, y -5..-3
}


@pytest.mark.parametrize("orientation", list(ATTACHED_SLOT_BOX))
def test_an_attached_table_hangs_on_the_turned_slots_side(orientation):
    result = measure(COIL, orientation, EIGHT, attach={"table": table(ROW, 2, "y")})
    assert result.slots["table"] == ATTACHED_SLOT_BOX[orientation]
    assert result.keepout == GridBox.union(result.body, *result.slots.values())


def test_a_taller_attached_table_grows_away_from_the_point():
    three = measure(
        COIL, Orientation.R0, EIGHT, attach={"table": table(table(ROW, 2, "y"), 3, "y")}
    )
    assert three.slots["table"] == GridBox(GridPoint(24, 8), GridPoint(40, 56))
    assert three.keepout.max == GridPoint(40, 56)


EDGE = build(
    Line(Point(0, 0), Point(4, 0)),
    Line(Point(0, 0), Point(0, 2)),
    slots=(Slot("table", Point(2, 2), Direction.S, (1, 1)),),
)


def _overlap(a, b):
    return min(a.max.x, b.max.x) > max(a.min.x, b.min.x) and min(a.max.y, b.max.y) > max(
        a.min.y, b.min.y
    )


@pytest.mark.parametrize("orientation", list(Orientation))
def test_the_attached_table_sits_outside_the_body(orientation):
    result = measure(EDGE, orientation, EIGHT, attach={"table": table(ROW, 2, "y")})
    assert result.slots["table"].max.x - result.slots["table"].min.x >= 16
    assert not _overlap(result.slots["table"], result.body)


def test_no_attach_changes_nothing():
    for orientation in Orientation:
        assert measure(COIL, orientation, EIGHT, attach={}) == measure(COIL, orientation, EIGHT)


def test_an_unknown_attach_key_names_the_key_and_the_slots():
    with pytest.raises(UnknownNameError, match=r"nope.*table"):
        measure(COIL, Orientation.R0, EIGHT, attach={"nope": ROW})


# D111: measure(stretch=) is measure of the stretched symbol, without building it.
FRAME = replace(
    build(
        Polyline((Point(0, 0), Point(8, 0), Point(8, 8), Point(0, 8)), closed=True),
        slots=(Slot("label", Point(1, 1), Direction.E, (4, 1)),),
    ),
    stretch=(Stretch("x", 4), Stretch("y", 4)),
)


@pytest.mark.parametrize("orientation", list(Orientation))
@pytest.mark.parametrize("length", [9, 20, 33, 112])
def test_measure_with_a_stretch_equals_measure_of_the_stretched_symbol(orientation, length):
    for lib in (EIGHT, Library("S", "S", "", {}, font=FONT)):
        for axis in ("x", "y"):
            direct = measure(FRAME, orientation, lib, stretch={axis: length})
            built = measure(stretch(FRAME, axis, length, grid=lib.grid), orientation, lib)
            assert direct == built


def test_the_axis_order_of_a_two_axis_stretch_does_not_change_the_measure():
    xy = stretch(stretch(FRAME, "x", 33, grid=EIGHT.grid), "y", 20, grid=EIGHT.grid)
    yx = stretch(stretch(FRAME, "y", 20, grid=EIGHT.grid), "x", 33, grid=EIGHT.grid)
    for orientation in (Orientation.R0, Orientation.R90):
        want = measure(xy, orientation, EIGHT)
        assert measure(yx, orientation, EIGHT) == want
        assert measure(FRAME, orientation, EIGHT, stretch={"x": 33, "y": 20}) == want
        assert measure(FRAME, orientation, EIGHT, stretch={"y": 20, "x": 33}) == want


def test_measure_with_a_stretch_raises_what_stretch_raises():
    with pytest.raises(InvalidValueError):
        measure(FRAME, Orientation.R0, EIGHT, stretch={"x": 2})
    with pytest.raises(InvalidValueError):
        measure(WIDE, Orientation.R0, EIGHT, stretch={"x": 20})
