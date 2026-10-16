"""Small accessors: `Box.union`, `slots_box`, `pole_pitch`, `pole_port`, `nodes_of` (D77)."""

from dataclasses import replace

import pytest

import symdef
from symdef.boxes import slot_box, slots_box
from symdef.geometry import Box, Direction, Line, Point
from symdef.model import Node, Port, Reference, Slot, Status, Symbol, SymbolKind
from symdef.repeat import pole_pitch, pole_port

E, W = Direction.E, Direction.W


def box(x0, y0, x1, y1):
    return Box(Point(x0, y0), Point(x1, y1))


def symbol(**fields):
    base = Symbol("t", SymbolKind.SYMBOL, Status.UNVERIFIED, Reference("X", "1"), ())
    return replace(base, **fields)


def test_union_of_one_box_is_that_box():
    assert Box.union(box(1, 2, 3, 4)) == box(1, 2, 3, 4)


def test_union_of_three_boxes_spans_all_of_them():
    assert Box.union(box(0, 0, 1, 1), box(-2, 3, 0, 4), box(5, -1, 6, 0)) == box(-2, -1, 6, 4)


def test_union_of_no_box_raises():
    with pytest.raises(ValueError, match="at least one box"):
        Box.union()


def test_slots_box_is_the_union_of_the_slot_boxes_without_the_body():
    east = Slot("a", Point(3, 4), E, (2, 1))
    west = Slot("b", Point(-1, 0), W, (4, 2))
    body = Line(Point(0, 0), Point(50, 0))
    got = slots_box(symbol(slots=(east, west), elements=(body,)))
    assert got == Box.union(slot_box(east), slot_box(west))
    assert got.max.x < 50


def test_slots_box_of_a_symbol_without_slots_is_the_origin_box():
    assert slots_box(symbol()) == box(0, 0, 0, 0)


def test_pole_pitch_defaults_to_four():
    assert pole_pitch(symbol()) == 4


def test_pole_pitch_is_the_explicit_pitch():
    assert pole_pitch(symbol(pole_pitch=6)) == 6


def test_pole_port_prefixes_the_pole_number():
    assert pole_port(2, "in") == "2.in"


def test_nodes_of_is_public_and_adds_one_node_per_unlisted_port():
    sym = symbol(
        ports=(Port("a", Point(0, 0), E), Port("b", Point(1, 0), W)), nodes=(Node(("a",)),)
    )
    assert symdef.nodes_of(sym) == (Node(("a",)), Node(("b",)))
    assert symdef.nodes_of.__doc__
