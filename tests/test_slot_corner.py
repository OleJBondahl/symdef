"""Slot corner sides (D131): a box that grows both ways from its opposite corner."""

import math
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from roundtrip import round_trips
from test_font import FONT

from symdef import (
    Box,
    Centre,
    Corner,
    Direction,
    Library,
    Line,
    Orientation,
    Point,
    Port,
    Reference,
    Slot,
    Status,
    Stretch,
    Symbol,
    SymbolKind,
    body_box,
    fitted_symbol,
    keepout_box,
    orient,
    orient_box,
    orient_point,
    slot_box,
    translate,
)
from symdef.font import text_width
from symdef.lint.geometry import stretch_cut
from symdef.load import parse_toml, symbol_from_data, validate
from symdef.serialize import symbol_to_data
from symdef.slottext import LINE_PITCH, slot_text, text_box
from symdef.units import Grid

TOML = """schema = 1
name = "c"
kind = "symbol"
status = "unverified"
reference = { standard = "X", number = "1" }
elements = [{ line = [[0, 0], [4, 0]] }]

[slots.tag]
at = [2, 2]
side = "SE"
box = [4, 2]
"""
BOXES = {
    Corner.NE: Box(Point(3, 3), Point(7, 5)),
    Corner.SE: Box(Point(3, 5), Point(7, 7)),
    Corner.SW: Box(Point(-1, 5), Point(3, 7)),
    Corner.NW: Box(Point(-1, 3), Point(3, 5)),
}


@pytest.mark.parametrize("side", list(Corner))
def test_a_corner_slot_grows_both_ways_from_its_point(side):
    assert slot_box(Slot("s", Point(3, 5), side, (4, 2))) == BOXES[side]


def test_an_se_slot_at_one_line_is_the_box_east_and_south_of_its_point():
    box = slot_box(Slot("s", Point(1, 0.5), Corner.SE, (6, 1)))
    assert (box.min, box.max) == (Point(1, 0.5), Point(7, 1.5))


@pytest.mark.parametrize(
    ("side", "turned"),
    [
        (Corner.SE, Corner.SW),
        (Corner.SW, Corner.NW),
        (Corner.NW, Corner.NE),
        (Corner.NE, Corner.SE),
    ],
)
def test_a_quarter_turn_carries_the_corner_with_it(side, turned):
    slot = Slot("s", Point(3, 5), side, (4, 2))
    from_symbol = _holder(slot)
    assert orient(from_symbol, Orientation.R90).slots[0].side is turned
    assert translate(from_symbol, 1, 1).slots[0].side is side


def test_a_mirror_swaps_the_east_and_west_of_the_corner():
    symbol = _holder(Slot("s", Point(3, 5), Corner.SE, (4, 2)))
    assert orient(symbol, Orientation.MR0).slots[0].side is Corner.SW


def test_a_corner_is_not_a_direction_and_a_port_cannot_be_one():
    assert Corner.SE not in set(Direction)
    assert (Corner.SE.horizontal, Corner.SE.vertical) == (Direction.E, Direction.S)
    assert (Corner.NW.horizontal, Corner.NW.vertical) == (Direction.W, Direction.N)
    data, _ = parse_toml(TOML + '\n[[ports]]\nid = "p"\nat = [0, 0]\ndir = "SE"\n')
    assert data is not None
    assert validate(data) != ()


def test_a_file_reads_writes_and_round_trips_a_corner_side():
    data, _ = parse_toml(TOML)
    assert data is not None
    assert validate(data) == ()
    symbol = symbol_from_data(data)
    assert symbol.slots[0].side is Corner.SE
    assert symbol_to_data(symbol)["slots"]["tag"]["side"] == "SE"
    assert round_trips(symbol)


def test_the_centre_and_direction_sides_still_read():
    for name, side in (("C", Centre.C), ("W", Direction.W)):
        data, _ = parse_toml(TOML.replace('"SE"', f'"{name}"'))
        assert data is not None
        assert symbol_from_data(data).slots[0].side is side


def _holder(slot):
    data, _ = parse_toml(TOML)
    assert data is not None
    return replace(symbol_from_data(data), slots=(slot,))


# fitted_symbol (D132): a corner slot and the body grow the same way, past the cut.
HEIGHT = 2
FIVE = "\n".join(["AB"] * 5)
LIB = Library(
    "S", "S", "", {}, font=FONT, grid=Grid(divisions_per_module=8), port_format="{k}.{port}"
)
CAP = 1.4  # with FONT at HEIGHT 2
TURNED = {Corner.NE: Corner.SE, Corner.SE: Corner.SW, Corner.SW: Corner.NW, Corner.NW: Corner.NE}
# A box 10 by 8 and a slot 6 by 2 on its left or right edge, cut across the slot's middle at y 4.
POSITIONS = {
    Corner.SE: Point(1, 3),
    Corner.NE: Point(1, 5),
    Corner.SW: Point(7, 3),
    Corner.NW: Point(7, 5),
}


def flag(side):
    return Symbol(
        "flag",
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", "1"),
        (Line(Point(0, 0), Point(10, 0)), Line(Point(0, 8), Point(10, 8))),
        ports=(Port("a", Point(0, 1), Direction.W), Port("b", Point(0, 7), Direction.W)),
        slots=(Slot("ref", POSITIONS[side], side, (6, 2)),),
        stretch=(Stretch("y", 4),),
    )


def growth_of(lines, tall):
    """The growth in modules a block of `lines` asks of a slot `tall`, worked apart from symdef."""
    need = CAP * (1 + LINE_PITCH * (lines - 1))
    return max(0.0, math.ceil(round(need * 8, 6)) / 8 - tall)


def growth(lines):
    """The growth a block of `lines` asks of the flag's slot, 2 tall."""
    return growth_of(lines, 2)


def test_an_se_slot_at_five_lines_grows_down_with_the_body_below_the_cut():
    result = fitted_symbol(flag(Corner.SE), {"ref": FIVE}, LIB, HEIGHT)
    grown = growth(5)
    assert grown == 7.875  # five lines need 9.875 modules in a slot 2 tall
    (slot,) = result.slots
    assert slot_box(slot) == Box(Point(1, 3), Point(7, 5 + grown))
    assert body_box(result) == Box(Point(0, 0), Point(10, 8 + grown))
    assert [p.position for p in result.ports] == [Point(0, 1), Point(0, 7 + grown)]


def test_one_line_asks_for_nothing_so_the_symbol_is_as_it_was():
    symbol = flag(Corner.SE)
    assert fitted_symbol(symbol, {"ref": "AB"}, LIB, HEIGHT) == symbol


@given(
    st.integers(1, 8), st.sampled_from(Corner), st.sampled_from([Orientation.R0, Orientation.R90])
)
def test_a_corner_slot_stays_in_the_body_at_r0_and_keeps_its_box_size_when_turned(
    lines, side, turn
):
    texts = {"ref": "\n".join(["AB"] * lines)}
    result = fitted_symbol(flag(side), texts, LIB, HEIGHT)
    grown = growth(lines)
    assert body_box(result) == Box(Point(0, 0), Point(10, 8 + grown))
    assert [p.position for p in result.ports] == [Point(0, 1), Point(0, 7 + grown)]
    (slot,) = result.slots
    held = text_box(slot, texts["ref"], HEIGHT, FONT, LIB.grid)
    assert Box.union(slot_box(slot), held) == slot_box(slot)
    assert Box.union(keepout_box(result, LIB.font), slot_box(slot)) == keepout_box(result, LIB.font)
    placed = orient(result, turn)
    assert body_box(placed) == orient_box(body_box(result), turn)
    assert keepout_box(placed, LIB.font) == body_box(placed)
    turned = placed.slots[0]
    assert turned.position == orient_point(slot.position, turn)
    assert turned.box == slot.box
    # a box is never rotated (R1592): the size is kept and no containment is asserted when turned
    assert (slot_box(turned).width, slot_box(turned).height) == (
        slot_box(slot).width,
        slot_box(slot).height,
    )
    assert turned.side is (side if turn is Orientation.R0 else TURNED[side])


@pytest.mark.parametrize("side", list(Corner))
def test_a_turned_corner_slot_grows_along_its_height_by_the_text_length(side):
    symbol = replace(flag(side), slots=(replace(flag(side).slots[0], turn=True, box=(2, 2)),))
    long = "ABiABAB"
    result = fitted_symbol(symbol, {"ref": long}, LIB, HEIGHT)
    need = math.ceil(round(text_width(FONT, long, HEIGHT) * 8, 6)) / 8
    (slot,) = result.slots
    assert slot_box(slot).height == need
    assert slot_box(slot).width == 2
    assert body_box(result).height == 8 + need - 2


@pytest.mark.parametrize(
    ("side", "anchor", "east"),
    [
        (Corner.NE, "start", 1.0),
        (Corner.SE, "end", 1.0),
        (Corner.SW, "end", 0.0),
        (Corner.NW, "start", 0.0),
    ],
)
def test_a_turned_corner_text_anchors_by_its_north_or_south_and_sits_by_its_east_or_west(
    side, anchor, east
):
    slot = Slot("s", Point(3, 4), side, (2, 1), turn=True)
    placed = slot_text(slot, "ABi", HEIGHT, FONT)
    assert (placed.anchor, placed.turned) == (anchor, True)
    assert placed.point == Point(3 + east * 1.4, 4)


# A cut across a slot outside the body (D133): the keepout grows, the body only moves.
def terminal():
    return Symbol(
        "terminal",
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", "1"),
        (Line(Point(0, -1), Point(4, -1)), Line(Point(0, 1), Point(4, 1))),
        slots=(Slot("tag", Point(0, -3.75), Corner.SE, (3, 1)),),
        stretch=(Stretch("y", -3.25),),
        keepout=Box(Point(0, -4), Point(4, 1)),
    )


def test_a_cut_across_a_slot_outside_the_body_builds_and_grows_the_keepout_not_the_body():
    symbol = terminal()
    assert stretch_cut(symbol) == ()
    result = fitted_symbol(symbol, {"tag": "\n".join(["AB"] * 3)}, LIB, HEIGHT)
    grown = growth_of(3, 1)
    assert grown > 0
    assert keepout_box(result, LIB.font) == Box(Point(0, -4), Point(4, 1 + grown))
    assert body_box(result).height == body_box(symbol).height
    assert body_box(result).min.y == body_box(symbol).min.y + grown
    assert slot_box(result.slots[0]).max.y == -2.75 + grown


def test_a_cut_across_no_slot_and_outside_the_body_is_still_refused():
    symbol = replace(terminal(), stretch=(Stretch("y", -6),))
    (found,) = stretch_cut(symbol)
    assert (found.rule, found.location) == ("stretch-cut", "stretch[0]")
    assert "across no slot box" in found.message
    assert stretch_cut(replace(terminal(), slots=(), stretch=(Stretch("y", -3.25),)))
