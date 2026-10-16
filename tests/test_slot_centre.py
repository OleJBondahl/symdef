"""Slot side `C` (SS18): the text centres on the slot point; the box is centred on it."""

import xml.etree.ElementTree as ET
from dataclasses import replace
from typing import Any

import pytest
from roundtrip import round_trips

from symdef import (
    Centre,
    Direction,
    Line,
    Orientation,
    Path,
    Point,
    Port,
    Reference,
    Slot,
    Status,
    Stretch,
    Symbol,
    SymbolKind,
    Weight,
    orient,
    repeat,
    slot_box,
    stretch,
    table,
    to_fragment,
    to_fragment_mm,
)
from symdef.load import parse_toml, symbol_from_data, validate
from symdef.serialize import symbol_to_data

MM: dict[str, Any] = {
    "module_mm": 2.5,
    "weights_mm": {Weight.NORMAL: 0.25},
    "dash_mm": (1.2, 0.6),
    "font_family": "sans-serif",
    "font_mm": 2.0,
    "cap_ratio": 0.7,
}
CAP_MM = 0.7 * 2.0


def sym(*, turn: bool = False, cuts=(), slot_at: Point | None = None) -> Symbol:
    return Symbol(
        name="t",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(Line(Point(0, 0), Point(20, 0)),),
        slots=(Slot("c", slot_at or Point(3, 5), Centre.C, (4.0, 2.0), turn),),
        stretch=cuts,
    )


def text_of(out: str) -> dict[str, str]:
    (found,) = ET.fromstring(out).iter("text")  # noqa: S314
    return {**found.attrib, "content": found.text or ""}


def test_the_centre_side_is_not_a_direction():
    assert Centre.C not in Direction
    assert Centre.C.name == "C"


def test_the_box_is_centred_on_the_slot_point():
    box = slot_box(sym().slots[0])
    assert (box.min, box.max) == (Point(1, 4), Point(5, 6))


def test_mm_text_centre_and_cap_middle_sit_on_the_point():
    t = text_of(to_fragment_mm(sym(), texts={"c": "A"}, **MM))
    assert t["text-anchor"] == "middle"
    assert float(t["x"]) == 3 * 2.5
    assert float(t["y"]) - CAP_MM / 2 == pytest.approx(5 * 2.5)
    assert "transform" not in t


def test_mm_turned_text_centres_across_its_reading_line():
    t = text_of(to_fragment_mm(sym(turn=True), texts={"c": "A"}, **MM))
    assert t["text-anchor"] == "middle"
    assert float(t["x"]) - CAP_MM / 2 == pytest.approx(3 * 2.5)
    assert float(t["y"]) == 5 * 2.5
    assert t["transform"].startswith("rotate(-90")


def test_module_text_centres_on_the_point():
    t = text_of(to_fragment(sym(), texts={"c": "A"}))
    cap = 0.72 * float(t["font-size"])
    assert t["text-anchor"] == "middle"
    assert float(t["x"]) == 3
    assert float(t["y"]) - cap / 2 == pytest.approx(5)


def test_module_turned_text_centres_on_the_point():
    t = text_of(to_fragment(sym(turn=True), texts={"c": "A"}))
    cap = 0.72 * float(t["font-size"])
    assert float(t["x"]) - cap / 2 == pytest.approx(3)
    assert float(t["y"]) == 5


@pytest.mark.parametrize("orientation", list(Orientation))
def test_orient_moves_only_the_point_of_a_centre_slot(orientation):
    before = sym(turn=True).slots[0]
    after = orient(sym(turn=True), orientation).slots[0]
    assert after.side is Centre.C
    assert (after.box, after.turn) == (before.box, before.turn)


def test_orient_keeps_the_box_centred_on_the_moved_point():
    after = orient(sym(), Orientation.R90).slots[0]
    box = slot_box(after)
    assert box.center == after.position


@pytest.mark.parametrize(
    "cuts", [(Stretch("x", 2),), (Stretch("x", 2), Stretch("x", 4, 3))], ids=["one", "two"]
)
def test_a_centre_slot_stays_at_its_box_centre_after_stretching(cuts):
    out = stretch(sym(cuts=cuts), "x", 30).slots[0]  # box x 1..5 spans both cuts
    box = slot_box(out)
    assert out.side is Centre.C
    assert box.center == out.position
    assert box.width > 4
    assert (box.min.x, box.max.x) != (1, 5)
    assert box.width == pytest.approx(4 + 10)


def test_a_centre_slot_beyond_a_cut_moves_and_keeps_its_box():
    out = stretch(sym(cuts=(Stretch("x", 0.5),), slot_at=Point(3, 5)), "x", 30).slots[0]
    assert out.box == (4.0, 2.0)
    assert out.position == Point(13, 5)


def test_table_and_repeat_keep_the_centre_side():
    base = replace(
        sym(),
        ports=(Port("in", Point(0, 0), Direction.W), Port("out", Point(4, 0), Direction.E)),
        paths=(Path("in", "out", "conductor", through=True),),
        slots=(Slot("marking.in", Point(3, 5), Centre.C, (4.0, 2.0)),),
    )
    assert table(base, 2, "x").slots[1].side is Centre.C
    assert repeat(base, 2).slots[0].side is Centre.C


TOML = """schema = 1
name = "c"
kind = "symbol"
status = "unverified"
reference = { standard = "X", number = "1" }
elements = [{ line = [[0, 0], [4, 0]] }]

[slots.tag]
at = [2, 2]
side = "C"
box = [4, 2]
"""


def test_a_file_reads_writes_and_round_trips_the_centre_side():
    data, _ = parse_toml(TOML)
    assert data is not None
    assert validate(data) == ()
    symbol = symbol_from_data(data)
    assert symbol.slots[0].side is Centre.C
    assert symbol_to_data(symbol)["slots"]["tag"]["side"] == "C"
    assert round_trips(symbol)


def test_a_port_or_an_anchor_cannot_be_centre():
    port = TOML + '\n[[ports]]\nid = "p"\nat = [0, 0]\ndir = "C"\n'
    anchor = TOML + '\n[[anchors]]\nid = "a"\nat = [0, 0]\ndir = "C"\n'
    for text in (port, anchor):
        data, _ = parse_toml(text)
        assert validate(data)
