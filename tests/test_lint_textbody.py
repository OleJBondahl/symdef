"""`text-outside-body`: a fixed text anchored in the body must lie wholly inside it (D90)."""

from symdef.font import FontMetrics
from symdef.geometry import Point, Polyline, Text, Weight
from symdef.lint.textbody import text_outside_body
from symdef.model import Reference, Severity, Status, Symbol, SymbolKind

FONT = FontMetrics("F", 1000, 700, 900, 200, {Weight.NORMAL: {"A": 500}, Weight.THICK: {}}, 600)
BODY = Polyline((Point(0, 0), Point(4, 0), Point(4, 2), Point(0, 2), Point(0, 0)))


def symbol(*elements):
    return Symbol("t", SymbolKind.SYMBOL, Status.UNVERIFIED, Reference("X", "S9"), elements)


def test_a_text_that_fits_gives_nothing():
    assert text_outside_body(symbol(BODY, Text("AA", Point(2, 1), 1)), FONT, 2.5) == ()


def test_a_text_that_overflows_names_the_symbol_the_text_and_the_millimetres():
    (found,) = text_outside_body(symbol(BODY, Text("AAAAAAAAAAAA", Point(2, 1), 1)), FONT, 2.5)
    assert (found.rule, found.severity, found.location) == (
        "text-outside-body",
        Severity.ERROR,
        "elements[1]",
    )
    assert "S9" in found.message
    assert "'AAAAAAAAAAAA'" in found.message
    assert "2.500 mm" in found.message


def test_a_text_anchored_outside_the_body_is_not_checked():
    assert text_outside_body(symbol(BODY, Text("A" * 30, Point(9, 1), 1)), FONT, 2.5) == ()


def test_a_symbol_with_no_other_element_is_not_checked():
    assert text_outside_body(symbol(Text("A" * 30, Point(0, 0), 1)), FONT, 2.5) == ()
