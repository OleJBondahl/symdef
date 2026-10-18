"""Slot text drawn by `to_fragment` and `to_fragment_mm` (D63)."""

import re
import xml.etree.ElementTree as ET
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from symdef import (
    Direction,
    Line,
    Point,
    Reference,
    Slot,
    Status,
    Symbol,
    SymbolKind,
    Weight,
    to_fragment,
    to_fragment_mm,
)
from symdef.errors import InvalidValueError, UnknownNameError

MM: dict[str, Any] = {
    "module_mm": 2.5,
    "weights_mm": {Weight.NORMAL: 0.25, Weight.THICK: 0.5},
    "dash_mm": (1.2, 0.6),
    "font_family": "Inter, sans-serif",
    "font_mm": 2.0,
    "cap_ratio": 0.7,
}
SLOTS = (
    Slot("n", Point(1, 1), Direction.N, (4.0, 1.0)),
    Slot("e", Point(2, 3), Direction.E, (4.0, 1.0)),
    Slot("s", Point(5, 6), Direction.S, (4.0, 1.0)),
    Slot("w", Point(7, 8), Direction.W, (4.0, 1.0)),
)
ALL = {"n": "N", "e": "E", "s": "S", "w": "W"}


def sym(slots=SLOTS):
    return Symbol(
        name="t",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(Line(Point(0, 0), Point(2, 0)),),
        slots=tuple(slots),
    )


def module(texts, **kw):
    return to_fragment(sym(), texts=texts, **kw)


def mm(texts, **kw):
    return to_fragment_mm(sym(), texts=texts, **MM, **kw)


def tags(out):
    return {t.text: t.attrib for t in ET.fromstring(out).iter("text")}  # noqa: S314


@pytest.mark.parametrize("draw", [module, mm])
def test_each_side_anchors_and_aligns_its_text(draw):
    t = tags(draw(ALL))
    assert [t[k]["text-anchor"] for k in "ENSW"] == ["start", "middle", "middle", "end"]


def test_module_positions():
    t = tags(module(ALL))
    assert (t["E"]["x"], t["E"]["y"]) == ("2", "3.36")
    assert (t["W"]["x"], t["W"]["y"]) == ("7", "8.36")
    assert (t["N"]["x"], t["N"]["y"]) == ("1", "1")
    assert (t["S"]["x"], t["S"]["y"]) == ("5", "6.72")


def test_mm_positions_are_module_times_point_plus_the_cap_term():
    t = tags(mm(ALL))
    cap = 0.7 * 2.0
    assert float(t["E"]["x"]) == 5
    assert float(t["E"]["y"]) == pytest.approx(7.5 + cap / 2)
    assert float(t["W"]["x"]) == 17.5
    assert float(t["W"]["y"]) == pytest.approx(20 + cap / 2)
    assert float(t["N"]["y"]) == 2.5
    assert float(t["S"]["y"]) == pytest.approx(15 + cap)
    assert t["N"]["font-size"] == "2"
    assert t["N"]["font-family"] == "Inter, sans-serif"


@pytest.mark.parametrize("draw", [module, mm])
def test_unknown_id_raises_naming_it_also_for_an_empty_string(draw):
    for text in ("x", ""):
        with pytest.raises(UnknownNameError, match="nope"):
            draw({"n": "A", "nope": text})


@pytest.mark.parametrize("draw", [module, mm])
def test_an_empty_string_draws_no_element(draw):
    assert draw({"n": ""}) == draw(None)
    assert draw({}) == draw(None)


@pytest.mark.parametrize("draw", [module, mm])
def test_muted_colours_the_slot_text(draw):
    out = draw({"n": "A"}, muted="grey")
    assert tags(out)["A"]["fill"] == "grey"
    assert "#000" not in out


@pytest.mark.parametrize("draw", [module, mm])
def test_the_slots_draw_in_id_order(draw):
    shuffled = {"w": "W", "s": "S", "e": "E", "n": "N"}
    out = draw(shuffled)
    assert re.findall(r">([NESW])</text>", out) == ["E", "N", "S", "W"]
    assert out == draw(ALL)


@pytest.mark.parametrize("draw", [module, mm])
def test_no_class_and_black_by_default(draw):
    out = draw({"n": "A"})
    assert "class=" not in out
    assert 'fill="#000" stroke="none"' in out.split("<text")[1]


@given(st.text())
def test_mm_never_measures_the_string(content):
    out = mm({"n": content})
    found = list(ET.fromstring(out).iter("text"))  # noqa: S314
    if content:
        assert len(found) == len(content.split("\n"))
        assert found[0].attrib["font-size"] == "2"
    else:
        assert not found


def ported(*ids, marked=()):
    from symdef import Direction, Port

    base = sym()
    return Symbol(
        name="p",
        kind=base.kind,
        status=base.status,
        reference=base.reference,
        elements=base.elements,
        ports=tuple(Port(i, Point(0, k), Direction.W) for k, i in enumerate(ids)),
        slots=(
            Slot("tag", Point(0, 5), Direction.E, (2.0, 1.0)),
            *(Slot(f"marking.{i}", Point(0, 9), Direction.N, (1.0, 1.0)) for i in marked),
        ),
    )


def mm_of(symbol, **kw):
    return to_fragment_mm(symbol, **MM, **kw)


@pytest.mark.parametrize("draw", [to_fragment, mm_of])
def test_a_missing_required_slot_raises_naming_it_and_the_symbol(draw):
    with pytest.raises(InvalidValueError, match=r"p: .*value"):
        draw(ported(), texts={"tag": "A"}, required_slots=("tag", "value"))


@pytest.mark.parametrize("draw", [to_fragment, mm_of])
def test_an_empty_string_satisfies_a_required_slot(draw):
    draw(ported(), texts={"tag": ""}, required_slots=("tag",))


@pytest.mark.parametrize("draw", [to_fragment, mm_of])
def test_texts_none_checks_nothing(draw):
    draw(ported(), required_slots=("tag", "value"))
    draw(ported(), texts=None, required_slots=("tag", "value"))


@pytest.mark.parametrize("draw", [to_fragment, mm_of])
def test_a_marking_entry_demands_one_slot_per_port(draw):
    with pytest.raises(InvalidValueError, match=r"marking\.1.*marking\.2"):
        draw(ported("1", "2"), texts={"tag": "A"}, required_slots=("marking.<port>",))
    both = ported("1", "2", marked=("1", "2"))
    draw(both, texts={"marking.1": "a", "marking.2": ""}, required_slots=("marking.<port>",))
    with pytest.raises(InvalidValueError, match=r"marking\.2$"):
        draw(both, texts={"marking.1": "a"}, required_slots=("marking.<port>",))
