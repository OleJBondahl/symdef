"""`to_fragment_mm(library=)`: widths and dashes come from the library (D116)."""

import re

import pytest
from hypothesis import given
from hypothesis import strategies as st

from symdef import (
    Arc,
    Circle,
    Line,
    Point,
    Polyline,
    Reference,
    Status,
    Style,
    Symbol,
    SymbolKind,
    Weight,
    table,
    to_fragment_mm,
    wire,
)
from symdef.errors import InvalidValueError, UnknownNameError
from symdef.model import Library, WireStyle
from symdef.svg import _num

LENGTH = st.floats(0.01, 5, allow_nan=False).map(lambda v: round(v, 3))
LINES = st.fixed_dictionaries(dict.fromkeys(Weight, LENGTH))
DASH = st.fixed_dictionaries(
    {
        "dashed": st.tuples(LENGTH, LENGTH),
        "dash_dot": st.tuples(LENGTH, LENGTH, LENGTH, LENGTH),
        "long": st.tuples(LENGTH, LENGTH),
    }
)
WEIGHTS = st.sampled_from(Weight)
STYLES = st.sampled_from(Style)
P = Point(0, 0)
ELEMENTS = st.one_of(
    st.builds(Line, st.just(P), st.just(Point(1, 0)), WEIGHTS, STYLES),
    st.builds(Polyline, st.just((P, Point(1, 1))), st.booleans(), weight=WEIGHTS, style=STYLES),
    st.builds(Circle, st.just(P), st.just(1.0), weight=WEIGHTS),
    st.builds(Arc, st.just(P), st.just(1.0), st.just(0.0), st.just(90.0), WEIGHTS, STYLES),
)


def sym(*elements):
    return Symbol("t", SymbolKind.SYMBOL, Status.UNVERIFIED, Reference("X", "1"), tuple(elements))


def draw(symbol, library=None, **given):
    return to_fragment_mm(
        symbol, library=library, module_mm=2.5, font_family="F", font_mm=2.0, cap_ratio=0.7, **given
    )


def tags(svg):
    return re.findall(r'stroke-width="([^"]+)"( stroke-dasharray="[^"]+")?', svg)


def expected(elements, library):
    out = []
    for e in elements:
        pattern = ""
        style = getattr(e, "style", Style.SOLID)
        key = {Style.DASHED: "dashed", Style.DASH_DOT: "dash_dot"}.get(style)
        if key:
            pattern = f' stroke-dasharray="{" ".join(_num(n) for n in library.dash[key])}"'
        out.append((_num(library.lines[e.weight]), pattern))
    return out


@given(LINES, DASH, st.lists(ELEMENTS, min_size=1, max_size=6))
def test_every_width_and_dash_of_a_symbol_is_the_librarys(lines, dash, elements):
    library = Library("s", "s", "", {}, lines=lines, dash=dash)
    assert tags(draw(sym(*elements), library)) == expected(elements, library)


@given(LINES, DASH, st.sampled_from(Weight), st.sampled_from(["solid", "dashed", "dash_dot"]))
def test_every_width_and_dash_of_a_wire_is_the_librarys(lines, dash, weight, style):
    wires = (WireStyle("w", weight, Style(style)),)
    library = Library("s", "s", "", {}, wires=wires, lines=lines, dash=dash)
    drawn = wire(library, "w", [(0, 0), (4, 0), (4, 6)])
    assert tags(draw(drawn, library)) == expected(drawn.elements, library)


@given(LINES, DASH, st.lists(ELEMENTS, min_size=1, max_size=3), st.integers(1, 4))
def test_every_width_and_dash_of_a_table_is_the_librarys(lines, dash, elements, n):
    library = Library("s", "s", "", {}, lines=lines, dash=dash)
    drawn = table(sym(*elements), n, "y")
    assert tags(draw(drawn, library)) == expected(drawn.elements, library)


LIBRARY = Library(
    "s",
    "s",
    "",
    {},
    lines=dict.fromkeys(Weight, 0.3),
    dash={"dashed": (1, 2), "dash_dot": (3, 4, 5, 6)},
)
DASHED = sym(Line(P, Point(1, 0), Weight.RULE, Style.DASHED))


def test_a_changed_library_changes_the_output():
    wide = LIBRARY.with_settings(lines=dict.fromkeys(Weight, 0.9), dash={"dashed": (7, 8)})
    assert tags(draw(DASHED, wide)) == [("0.9", ' stroke-dasharray="7 8"')]


def test_an_explicit_argument_beats_the_library():
    svg = draw(DASHED, LIBRARY, weights_mm={Weight.RULE: 0.5}, dash_mm=(9, 9))
    assert tags(svg) == [("0.5", ' stroke-dasharray="9 9"')]
    dotted = sym(Line(P, Point(1, 0), Weight.RULE, Style.DASH_DOT))
    assert (
        tags(draw(dotted, LIBRARY, dash_dot_mm=(1, 1, 1, 1)))[0][1] == ' stroke-dasharray="1 1 1 1"'
    )


def test_a_call_without_a_library_keeps_the_explicit_output():
    svg = draw(DASHED, weights_mm={Weight.RULE: 0.18}, dash_mm=(1.25, 0.625))
    assert tags(svg) == [("0.18", ' stroke-dasharray="1.25 0.625"')]


def test_a_missing_width_names_the_weight_and_the_two_ways_to_give_it():
    solid = sym(Line(P, Point(1, 0), Weight.RULE))
    with pytest.raises(UnknownNameError, match=r"no width for RULE.*weights_mm.*\[lines\]"):
        draw(solid, Library("s", "s", "", {}, lines={Weight.NORMAL: 0.2}))
    with pytest.raises(UnknownNameError, match="no width for RULE"):
        draw(solid)


def test_a_missing_dashed_pattern_names_the_key():
    library = Library("s", "s", "", {}, lines={Weight.RULE: 0.2})
    with pytest.raises(UnknownNameError, match=r"dashed.*dash_mm.*\[dash\]"):
        draw(DASHED, library)


def test_a_missing_dash_dot_pattern_names_the_key_and_the_argument():
    library = Library("s", "s", "", {}, lines={Weight.RULE: 0.2}, dash={"dashed": (1, 1)})
    dotted = sym(Line(P, Point(1, 0), Weight.RULE, Style.DASH_DOT))
    with pytest.raises(InvalidValueError, match=r"dash_dot_mm.*dash_dot"):
        draw(dotted, library)


def test_a_muted_symbol_takes_its_dash_from_the_librarys_normal_width():
    svg = draw(DASHED, LIBRARY.with_settings(lines=dict.fromkeys(Weight, 0.4)), muted="#999")
    assert 'stroke-dasharray="0.4 0.4"' in svg
