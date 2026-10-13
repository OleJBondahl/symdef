import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from svg_golden_symbols import GOLDEN_SYMBOLS

from symdef import (
    Arc,
    Circle,
    Fill,
    Line,
    Point,
    Polyline,
    Reference,
    Status,
    Style,
    Symbol,
    SymbolKind,
    Text,
    Weight,
    to_fragment,
    to_fragment_mm,
    to_svg,
)

NS = "{http://www.w3.org/2000/svg}"
GOLDEN = Path(__file__).parent / "fixtures" / "svg_golden"
WEIGHTS = {Weight.NORMAL: 0.25, Weight.THICK: 0.5}


def sym(*elements):
    return Symbol(
        name="t",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=tuple(elements),
    )


def everything():
    return sym(
        Line(Point(0, 0), Point(2, 1)),
        Polyline((Point(0, 0), Point(2, 0), Point(2, 3))),
        Circle(Point(1, 1), 0.5),
        Arc(Point(2, 2), 1.5, 0, 90, weight=Weight.THICK),
        Line(Point(0, 3), Point(4, 3), style=Style.DASHED),
        Text("A", Point(3, 2), height=0.8),
    )


def render(module_mm, symbol=None, *, weights_mm=None, font_family="Inter, sans-serif"):
    return to_fragment_mm(
        symbol or everything(),
        module_mm=module_mm,
        weights_mm=weights_mm or WEIGHTS,
        dash_mm=(1.2, 0.6),
        font_family=font_family,
        font_mm=2.0,
        cap_ratio=0.7,
    )


def elements(out):
    return list(ET.fromstring(out))  # noqa: S314 - parses this library's own output


def floats(text):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]


def test_absolute_sizes_do_not_change_with_the_module_and_coordinates_scale():
    small, large = elements(render(2.5)), elements(render(3.0))
    for a, b in zip(small, large, strict=True):
        for key in ("stroke-width", "stroke-dasharray", "font-size"):
            assert a.get(key) == b.get(key)
    assert [e.get("stroke-width") for e in small[:5]] == ["0.25", "0.25", "0.25", "0.5", "0.25"]
    assert small[4].get("stroke-dasharray") == "1.2 0.6"
    assert small[5].get("font-size") == "2"
    ratio = 3.0 / 2.5
    for key in ("x1", "y1", "x2", "y2"):
        assert float(large[0].get(key)) == pytest.approx(float(small[0].get(key)) * ratio)
    assert floats(large[1].get("points")) == pytest.approx(
        [v * ratio for v in floats(small[1].get("points"))]
    )
    for key in ("cx", "cy", "r"):
        assert float(large[2].get(key)) == pytest.approx(float(small[2].get(key)) * ratio)
    # M, A rx ry rot large sweep, end: the radius and both points scale, rotation and flags do not.
    d_small, d_large = floats(small[3].get("d")), floats(large[3].get("d"))
    assert d_large == pytest.approx(
        [v * ratio if i not in (4, 5, 6) else v for i, v in enumerate(d_small)]
    )
    assert large[3].get("d").startswith("M 10.5 6 A 4.5 4.5 0 0 1 6 10.5")


def test_no_scale_and_no_transform():
    out = render(3.0)
    assert "scale(" not in out
    assert "transform" not in out


def test_text_is_centred_by_the_cap_ratio_in_the_callers_family():
    text = elements(render(3.0, font_family='My "Face"'))[5]
    assert text.get("x") == "9"
    assert float(text.get("y")) == pytest.approx(2 * 3.0 + 0.7 * 2.0 / 2)
    assert text.get("text-anchor") == "middle"
    assert text.get("font-family") == 'My "Face"'
    assert text.text == "A"


def test_solid_fill_is_still_black():
    out = render(3.0, sym(Circle(Point(1, 1), 0.5, fill=Fill.SOLID)))
    assert elements(out)[0].get("fill") == "#000"


def test_a_missing_weight_raises_key_error_naming_it():
    with pytest.raises(KeyError, match="THICK"):
        render(3.0, weights_mm={Weight.NORMAL: 0.25})


@pytest.mark.parametrize("name", sorted(GOLDEN_SYMBOLS))
def test_to_fragment_and_to_svg_bytes_are_unchanged(name):
    symbol = GOLDEN_SYMBOLS[name]
    assert to_fragment(symbol) == (GOLDEN / f"{name}.fragment.svg").read_text(encoding="utf-8")
    assert to_svg(symbol) == (GOLDEN / f"{name}.svg").read_text(encoding="utf-8")


def test_a_full_circle_arc_is_two_scaled_half_arcs():
    out = render(3.0, sym(Arc(Point(2, 2), 1, 0, 0)))
    assert elements(out)[0].get("d") == "M 9 6 A 3 3 0 0 1 3 6 A 3 3 0 0 1 9 6"
