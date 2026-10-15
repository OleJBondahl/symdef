"""`muted`: a not-installed look in the caller's colour, for both fragment functions."""

import re

import pytest

from symdef.geometry import Arc, Circle, Fill, Line, Point, Polyline, Style, Text, Weight
from symdef.model import Reference, Status, Symbol, SymbolKind
from symdef.svg import to_fragment
from symdef.svg_mm import to_fragment_mm

WEIGHTS = {Weight.NORMAL: 0.25, Weight.THICK: 0.5}
GREY = "#888"


def sym():
    return Symbol(
        name="t",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(
            Line(Point(0, 0), Point(2, 0), Weight.THICK),
            Line(Point(0, 1), Point(2, 1), style=Style.DASHED),
            Line(Point(0, 2), Point(2, 2), style=Style.DASH_DOT),
            Circle(Point(1, 1), 0.5, fill=Fill.SOLID),
            Polyline((Point(0, 0), Point(1, 1), Point(2, 0)), closed=True, fill=Fill.TINT),
            Polyline((Point(0, 0), Point(1, 1), Point(2, 0)), closed=True),
            Arc(Point(2, 2), 1, 0, 90, style=Style.DASHED),
            Text("A", Point(1, 1)),
        ),
    )


def mm(symbol, *, muted=None, tint=None, **extra):
    return to_fragment_mm(
        symbol,
        module_mm=2.5,
        weights_mm=WEIGHTS,
        dash_mm=(1.2, 0.6),
        font_family="sans-serif",
        font_mm=2.0,
        cap_ratio=0.7,
        muted=muted,
        tint=tint,
        **extra,
    )


def unit(symbol, *, muted=None, tint=None):
    return to_fragment(symbol, muted=muted, tint=tint)


CASES = [(unit, "0.1"), (mm, "0.25")]


@pytest.mark.parametrize(("draw", "normal"), CASES)
def test_a_muted_symbol_has_no_black_and_one_dash_pattern(draw, normal):
    out = draw(sym(), muted=GREY, tint="#f00")
    assert "#000" not in out
    assert "#f00" not in out
    assert set(re.findall(r'stroke-dasharray="([^"]*)"', out)) == {f"{normal} {normal}"}
    assert out.count("stroke-dasharray") == 7
    assert out.startswith(f'<g fill="none" stroke="{GREY}"')


@pytest.mark.parametrize("draw", [unit, mm])
def test_fills_and_text_take_the_colour_and_unfilled_shapes_stay_unfilled(draw):
    out = draw(sym(), muted=GREY)
    assert out.count(f'fill="{GREY}"') == 3  # solid circle, tint polyline, text
    assert re.search(rf'<text [^>]*fill="{GREY}" stroke="none"', out)
    assert "stroke-dasharray" not in out.split("<text")[1]
    polygons = re.findall(r"<polygon [^>]*/>", out)
    assert [("fill=" in p) for p in polygons] == [True, False]


@pytest.mark.parametrize("draw", [unit, mm])
def test_not_muted_keeps_black(draw):
    extra = {} if draw is unit else {"dash_dot_mm": (4, 1, 0.25, 1)}
    out = draw(sym(), **extra)
    assert out.count('fill="#000"') == 2  # solid circle, text
    assert "#888" not in out


def test_a_muted_millimetre_draw_needs_no_dash_keywords():
    assert mm(sym(), muted=GREY)  # no dash_dot_mm, and dash_mm is not read


def test_a_muted_millimetre_draw_needs_the_normal_weight():
    with pytest.raises(KeyError, match="NORMAL"):
        to_fragment_mm(
            sym(),
            module_mm=2.5,
            weights_mm={Weight.THICK: 0.5},
            dash_mm=(1, 1),
            font_family="f",
            font_mm=2,
            cap_ratio=0.7,
            muted=GREY,
        )


@pytest.mark.parametrize("draw", [unit, mm])
def test_a_bad_colour_is_refused_even_for_a_symbol_without_fills(draw):
    with pytest.raises(ValueError, match="muted must be"):
        draw(sym(), muted='x" onload="y')


def test_the_millimetre_stroke_is_muted_too():
    out = mm(sym(), muted="grey")
    assert 'stroke="grey"' in out
