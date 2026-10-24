"""`turn = true`: a slot whose string reads bottom-up (D65)."""

import tomllib
import xml.etree.ElementTree as ET
from dataclasses import replace
from typing import Any

import pytest

from symdef import (
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
    stretch,
    table,
    to_fragment,
    to_fragment_mm,
)
from symdef.load import symbol_from_data, validate
from symdef.serialize import symbol_to_data

N, E, S, W = Direction.N, Direction.E, Direction.S, Direction.W
MM: dict[str, Any] = {
    "module_mm": 2.5,
    "weights_mm": {Weight.NORMAL: 0.25},
    "dash_mm": (1.2, 0.6),
    "font_family": "sans-serif",
    "font_mm": 2.0,
    "cap_ratio": 0.7,
}
TURNED = tuple(Slot(f"t{s.name}", Point(10, 10), s, (1.0, 6.0), turn=True) for s in (N, E, S, W))
FILE = """
schema = 1
name = "X"
kind = "symbol"
status = "unverified"
reference = { standard = "S", number = "1" }
elements = [ { line = [[0, 0], [2, 0]] } ]
[slots]
a = { at = [0, 1], side = "E", box = [1, 4], turn = true }
b = { at = [0, 2], side = "E", box = [4, 1] }
"""


def sym(*slots, ports=()):
    return Symbol(
        name="t",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(Line(Point(0, 0), Point(2, 0)),),
        ports=ports,
        slots=slots,
        stretch=(Stretch("x", 1),),
    )


def tags(out):
    return {t.text: t.attrib for t in ET.fromstring(out).iter("text")}  # noqa: S314


def test_the_file_key_loads_serialises_and_defaults_to_false():
    data = tomllib.loads(FILE)
    assert validate(data) == ()
    slots = {s.id: s for s in symbol_from_data(data).slots}
    assert (slots["a"].turn, slots["b"].turn) == (True, False)
    written = symbol_to_data(symbol_from_data(data))["slots"]
    assert written["a"]["turn"] is True
    assert "turn" not in written["b"]


def test_a_bad_turn_value_is_a_finding():
    assert validate(tomllib.loads(FILE.replace("turn = true", 'turn = "yes"')))


@pytest.mark.parametrize("orientation", list(Orientation))
def test_orient_never_changes_turn_and_the_text_is_never_turned_by_it(orientation):
    symbol = orient(sym(TURNED[0], replace(TURNED[0], id="h", turn=False)), orientation)
    assert [s.turn for s in symbol.slots] == [True, False]
    for draw in (
        lambda: to_fragment(symbol, texts={"tN": "A", "h": "B"}),
        lambda: to_fragment_mm(symbol, texts={"tN": "A", "h": "B"}, **MM),
    ):
        t = tags(draw())
        assert t["A"]["transform"].startswith("rotate(-90 ")
        assert "transform" not in t["B"]


@pytest.mark.parametrize("draw", ["module", "mm"])
def test_turned_alignment_per_side(draw):
    symbol = sym(*TURNED)
    texts = {s.id: s.side.name for s in TURNED}
    out = (
        to_fragment(symbol, texts=texts)
        if draw == "module"
        else to_fragment_mm(symbol, texts=texts, **MM)
    )
    t = tags(out)
    assert [t[k]["text-anchor"] for k in "NSEW"] == ["start", "end", "middle", "middle"]
    unit = 1.0 if draw == "module" else 2.5
    xs = {k: float(t[k]["x"]) / unit for k in "NSEW"}
    cap = 0.72 * 1.0 if draw == "module" else 0.7 * 2.0 / 2.5
    assert xs["W"] == pytest.approx(10)
    assert xs["N"] == pytest.approx(10 + cap / 2)
    assert xs["S"] == pytest.approx(10 + cap / 2)
    assert xs["E"] == pytest.approx(10 + cap)
    for k in "NSEW":
        assert float(t[k]["y"]) / unit == pytest.approx(10)
        assert t[k]["transform"] == f"rotate(-90 {t[k]['x']} {t[k]['y']})"


def test_the_module_size_fits_along_the_height():
    text = "a" * 20
    t = tags(to_fragment(sym(TURNED[0]), texts={"tN": text}))
    assert float(t[text]["font-size"]) == pytest.approx(0.5)  # 6 / (0.6 * 20), not 1 / 12


def test_texts_none_draws_nothing_for_a_turned_slot():
    symbol = sym(*TURNED)
    assert to_fragment(symbol) == to_fragment(replace(symbol, slots=()))
    assert "transform" not in to_fragment(symbol, texts={})


def test_turn_survives_repeat_table_stretch():
    marking = Slot("marking.in", Point(0, 3), S, (1.0, 3.0), turn=True)
    ports = (Port("in", Point(0, 0), N), Port("out", Point(0, 4), S))
    symbol = replace(
        sym(marking, replace(TURNED[0], id="tag"), ports=ports),
        paths=(Path("in", "out", "conductor", through=True),),
    )
    assert all(s.turn for s in repeat(symbol, 2, port_format="{k}.{port}").slots)
    assert all(s.turn for s in table(symbol, 2, "y", port_format="{k}.{port}").slots)
    assert all(s.turn for s in stretch(symbol, "x", 5).slots)
