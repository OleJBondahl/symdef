"""Slot corner sides (D131): a box that grows both ways from its opposite corner."""

from dataclasses import replace

import pytest
from roundtrip import round_trips

from symdef import (
    Box,
    Centre,
    Corner,
    Direction,
    Orientation,
    Point,
    Slot,
    orient,
    slot_box,
    translate,
)
from symdef.load import parse_toml, symbol_from_data, validate
from symdef.serialize import symbol_to_data

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
