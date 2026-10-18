"""Multi-line slot text (D95): one placement per line, stacked away from the slot's side."""

import xml.etree.ElementTree as ET
from typing import Any

import pytest

from symdef import (
    Centre,
    Direction,
    Line,
    Point,
    Reference,
    Slot,
    Status,
    Symbol,
    SymbolKind,
    Weight,
    slot_box,
    to_fragment,
    to_fragment_mm,
)
from symdef.font import text_width
from symdef.slottext import LINE_PITCH, slot_lines, slot_text, stack_shifts, text_box

MM: dict[str, Any] = {
    "module_mm": 2.5,
    "weights_mm": {Weight.NORMAL: 0.25},
    "dash_mm": (1.2, 0.6),
    "font_family": "sans-serif",
    "font_mm": 2.0,
    "cap_ratio": 0.7,
}
CAP_MM = 0.7 * 2.0
HEIGHT = 2
CAP = 0.72 * HEIGHT
SIDES = [Direction.N, Direction.E, Direction.S, Direction.W, Centre.C]


def slot_of(side, *, turn: bool = False) -> Slot:
    return Slot("c", Point(3, 5), side, (4.0, 2.0), turn)


def sym(texts_slot: Slot) -> Symbol:
    return Symbol(
        name="t",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(Line(Point(0, 0), Point(20, 0)),),
        slots=(texts_slot,),
    )


def texts_of(out: str) -> list[dict[str, str]]:
    return [dict(t.attrib) for t in ET.fromstring(out).iter("text")]  # noqa: S314


@pytest.mark.parametrize("turn", [False, True])
@pytest.mark.parametrize("side", SIDES)
def test_a_one_line_text_is_the_slot_text_placement(side, turn):
    slot = slot_of(side, turn=turn)
    assert slot_lines(slot, "AB", HEIGHT, None) == (slot_text(slot, "AB", HEIGHT, None),)


def test_two_lines_stack_south_about_the_centre_point_in_module_units():
    slot = slot_of(Centre.C)
    first, second = slot_lines(slot, "AB\nCD", HEIGHT, None)
    mid_y = (first.point.y + second.point.y) / 2
    assert (first.point.x, second.point.x) == (3, 3)
    assert mid_y == pytest.approx(slot_text(slot, "AB", HEIGHT, None).point.y)
    assert second.point.y - first.point.y == pytest.approx(LINE_PITCH * CAP)


def test_two_lines_reach_fragment_as_two_text_elements():
    slot = slot_of(Centre.C)
    out = to_fragment(sym(slot), texts={"c": "AB\nCD"})
    first, second = texts_of(out)
    cap = 0.72 * float(first["font-size"])
    assert (first["x"], second["x"]) == ("3", "3")
    assert float(second["y"]) - float(first["y"]) == pytest.approx(LINE_PITCH * cap, abs=1e-2)
    assert (float(first["y"]) + float(second["y"])) / 2 == pytest.approx(5 + 0.5 * cap, abs=1e-2)


def test_two_lines_reach_the_mm_fragment_as_two_text_elements():
    slot = slot_of(Centre.C)
    out = to_fragment_mm(sym(slot), texts={"c": "AB\nCD"}, **MM)
    first, second = texts_of(out)
    assert float(second["y"]) - float(first["y"]) == pytest.approx(LINE_PITCH * CAP_MM, abs=1e-2)


def test_a_turned_centre_block_stacks_west_to_east_with_the_first_line_westmost():
    slot = slot_of(Centre.C, turn=True)
    first, second = slot_lines(slot, "AB\nCD", HEIGHT, None)
    assert first.turned
    assert second.turned
    assert first.point.y == second.point.y == 5
    assert first.point.x < second.point.x
    assert second.point.x - first.point.x == pytest.approx(LINE_PITCH * CAP)
    assert first.anchor == second.anchor == "middle"


def test_text_box_of_two_lines_is_the_union_of_its_lines():
    slot = slot_of(Centre.C)
    box = text_box(slot, "AB\nCDE", HEIGHT, None)
    longer = text_width(None, "CDE", HEIGHT)
    assert box.max.x - box.min.x == pytest.approx(longer)
    assert box.max.y - box.min.y == pytest.approx(CAP + LINE_PITCH * CAP)


def test_text_box_of_one_line_is_one_cap_high_and_the_line_wide():
    box = text_box(slot_of(Centre.C), "AB", HEIGHT, None)
    assert box.max.x - box.min.x == pytest.approx(text_width(None, "AB", HEIGHT))
    assert box.max.y - box.min.y == pytest.approx(CAP)


def test_a_north_side_block_grows_up_so_its_last_line_sits_on_the_baseline():
    slot = slot_of(Direction.N)
    assert stack_shifts(slot, 2) == (-LINE_PITCH, 0.0)
    lines = slot_lines(slot, "AB\nCD", HEIGHT, None)
    assert lines[-1] == slot_text(slot, "AB", HEIGHT, None)


def test_a_south_side_block_grows_down_so_its_first_line_sits_on_the_baseline():
    slot = slot_of(Direction.S)
    assert stack_shifts(slot, 2) == (0.0, LINE_PITCH)
    lines = slot_lines(slot, "AB\nCD", HEIGHT, None)
    assert lines[0] == slot_text(slot, "AB", HEIGHT, None)


def test_a_turned_west_block_grows_west():
    assert stack_shifts(slot_of(Direction.W, turn=True), 2) == (-LINE_PITCH, 0.0)


def test_a_turned_east_block_grows_east():
    assert stack_shifts(slot_of(Direction.E, turn=True), 2) == (0.0, LINE_PITCH)


def test_slot_box_with_a_block_taller_than_the_reserved_box_grows_it():
    slot = slot_of(Centre.C)
    reserved = slot_box(slot)
    grown = slot_box(slot, "AB\nCD", HEIGHT, None)
    assert reserved.max.y - reserved.min.y == pytest.approx(2.0)
    assert grown.max.y - grown.min.y > reserved.max.y - reserved.min.y


def test_the_pitch_is_one_and_a_half_cap_heights_written_out():
    """Fixed numbers, so the pitch cannot drift with the constant the other tests read."""
    from symdef import Centre, Point, Slot, slot_lines

    slot = Slot("c", Point(3, 5), Centre.C, (4, 1))
    first, second = slot_lines(slot, "AB\nCD", 2, None)
    assert first.point.y == pytest.approx(5 + 0.72 - 0.75 * 1.44)
    assert second.point.y == pytest.approx(5 + 0.72 + 0.75 * 1.44)
