"""The tint fill: a closed polyline takes the caller's colour, checked before it reaches markup."""

import pytest

from symdef import (
    Circle,
    Fill,
    Point,
    Polyline,
    Reference,
    Status,
    Symbol,
    SymbolKind,
    Weight,
    to_fragment,
    to_fragment_mm,
    to_svg,
)
from symdef.load import symbol_from_data, validate
from symdef.serialize import symbol_to_data

WEIGHTS = {Weight.NORMAL: 0.25, Weight.THICK: 0.5}
TRIANGLE = (Point(0, 0), Point(2, 0), Point(2, 2))


def sym(*elements):
    return Symbol(
        name="t",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=tuple(elements),
    )


def tinted(fill=Fill.TINT):
    return sym(Polyline(TRIANGLE, closed=True, fill=fill))


def to_mm(symbol, tint):
    return to_fragment_mm(
        symbol,
        module_mm=2.5,
        weights_mm=WEIGHTS,
        dash_mm=(1.2, 0.6),
        font_family="sans-serif",
        font_mm=2.0,
        cap_ratio=0.7,
        tint=tint,
    )


def render_all(symbol, tint):
    """Render through the three public entry points that take a tint."""
    return {
        "fragment": to_fragment(symbol, tint=tint),
        "svg": to_svg(symbol, tint=tint),
        "mm": to_mm(symbol, tint),
    }


def polygon_lines(out):
    return [line for line in out.splitlines() if "<polygon" in line]


@pytest.mark.parametrize("entry", ["fragment", "svg", "mm"])
def test_a_tinted_closed_polyline_takes_the_passed_colour(entry):
    out = render_all(tinted(), "#aabbcc")[entry]
    assert 'fill="#aabbcc"' in polygon_lines(out)[0]


@pytest.mark.parametrize("entry", ["fragment", "svg", "mm"])
def test_a_tinted_polyline_without_a_tint_is_unfilled(entry):
    out = render_all(tinted(), None)[entry]
    assert 'fill="none"' in polygon_lines(out)[0]
    assert "#aabbcc" not in out


def test_a_solid_polyline_ignores_the_tint():
    out = to_fragment(sym(Polyline(TRIANGLE, closed=True, fill=Fill.SOLID)), tint="#aabbcc")
    assert 'fill="#000"' in polygon_lines(out)[0]
    assert "#aabbcc" not in out


def test_a_hand_built_tinted_circle_takes_the_colour_and_none_without_one():
    circle = sym(Circle(Point(0, 0), 1, Fill.TINT))
    assert 'fill="red"' in to_fragment(circle, tint="red")
    assert 'fill="none"' in to_fragment(circle)


@pytest.mark.parametrize("colour", ['red;"onload=', "url(#x)", "", "#12", "#ggg", "#abcd"])
def test_a_bad_colour_is_refused(colour):
    symbol = tinted()
    with pytest.raises(ValueError, match="tint must be"):
        to_fragment(symbol, tint=colour)
    with pytest.raises(ValueError, match="tint must be"):
        to_svg(symbol, tint=colour)
    with pytest.raises(ValueError, match="tint must be"):
        to_mm(symbol, colour)


def test_a_bad_colour_is_refused_even_with_no_tinted_element():
    with pytest.raises(ValueError, match="tint must be"):
        to_fragment(sym(), tint="url(#x)")


@pytest.mark.parametrize("colour", ["red", "#abc", "#A1b2C3"])
def test_a_good_colour_is_accepted(colour):
    assert f'fill="{colour}"' in to_fragment(tinted(), tint=colour)


def test_a_file_tint_round_trips_through_the_resolved_form():
    data = {
        "schema": 1,
        "name": "Fixture",
        "kind": "symbol",
        "status": "unverified",
        "reference": {"standard": "IEC 60617", "number": "S00001"},
        "ports": [],
        "elements": [{"polyline": [[0, 0], [1, 0], [1, 1]], "closed": True, "fill": "tint"}],
        "slots": {},
    }
    assert validate(data) == ()
    symbol = symbol_from_data(data)
    element = symbol.elements[0]
    assert isinstance(element, Polyline)
    assert element.fill is Fill.TINT
    resolved = symbol_to_data(symbol)
    assert resolved["elements"][0]["fill"] == "tint"
    assert symbol_from_data(resolved).elements == symbol.elements
