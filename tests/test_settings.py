"""`Library.with_settings`: a validated replace of module, font, heights and line widths (D88)."""

from dataclasses import replace
from pathlib import Path

import pytest

from symdef import load_library
from symdef.errors import InvalidValueError
from symdef.font import FontMetrics
from symdef.geometry import Point, Polyline, Style, Text, Weight
from symdef.model import Library, Reference, Status, Symbol, SymbolKind, WireStyle
from symdef.settings import with_settings

DATA = Path(__file__).resolve().parent / "data" / "dejavu"
REGULAR = (DATA / "DejaVuSansCondensed.ttf").read_bytes()
BOLD = (DATA / "DejaVuSansCondensed-Bold.ttf").read_bytes()
FONT = FontMetrics(
    "F",
    1000,
    700,
    900,
    200,
    {Weight.NORMAL: {"A": 500}, Weight.THICK: {}},
    {Weight.NORMAL: 600, Weight.THICK: 600},
)


def symbol(number="S1", height=0.5):
    return Symbol(
        "t",
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", number),
        (Text("M", Point(0, 0), height),),
    )


def library(*symbols, **fields):
    chosen = symbols or (symbol(),)
    wires = (WireStyle("w", Weight.THICK, Style.SOLID),)
    return Library("s", "s", "", {s.reference.number: s for s in chosen}, wires=wires, **fields)


def test_an_unchanged_call_returns_an_equal_library():
    base = library(font=FONT)
    assert base.with_settings() == base
    assert with_settings(base) == base


def test_the_library_of_a_real_set_comes_back_equal():
    base = load_library(Path(__file__).resolve().parent / "fixtures" / "guide")
    assert base.with_settings() == base


def test_module_mm_alone_replaces_the_module_and_keeps_the_rest():
    base = library(font=FONT)
    result = base.with_settings(module_mm=2.0)
    assert result.grid == replace(base.grid, module_mm=2.0)
    assert (result.font, result.lines, result.symbols) == (base.font, base.lines, base.symbols)


@pytest.mark.parametrize("bad", [0, -1, "2.5", True, float("nan")])
def test_a_bad_module_raises_symdefs_error(bad):
    with pytest.raises(InvalidValueError, match="module_mm"):
        library().with_settings(module_mm=bad)


def test_font_alone_is_measured_and_keeps_the_heights():
    base = library(font=replace(FONT, heights={"body": 2.0}))
    result = base.with_settings(font=(REGULAR, BOLD))
    assert result.font is not None
    assert result.font.name == "DejaVu Sans Condensed"
    assert result.font.advances[Weight.NORMAL]["A"] == 1260
    assert dict(result.font.heights) == {"body": 2.0}
    assert (result.grid, result.lines) == (base.grid, base.lines)


@pytest.mark.parametrize("bad", [b"x", (REGULAR,), (REGULAR, "bold"), [REGULAR, BOLD]])
def test_a_bad_font_raises(bad):
    with pytest.raises(InvalidValueError, match=r"font|TrueType"):
        library().with_settings(font=bad)


def test_a_font_with_no_usable_face_raises_through_the_measure():
    with pytest.raises(InvalidValueError, match="TrueType"):
        library().with_settings(font=(b"no", b"no"))


def test_heights_alone_replace_them():
    result = library(font=FONT).with_settings(heights={"body": 3.5})
    assert result.font is not None
    assert dict(result.font.heights) == {"body": 3.5}
    assert result.font.advances == library(font=FONT).font.advances


@pytest.mark.parametrize("bad", [{"body": 0}, {"body": "2"}, {1: 2.0}, [("body", 2.0)]])
def test_bad_heights_raise(bad):
    with pytest.raises(InvalidValueError, match="height"):
        library(font=FONT).with_settings(heights=bad)


def test_heights_without_any_font_raise():
    with pytest.raises(InvalidValueError, match="need a font"):
        library().with_settings(heights={"body": 2.0})


def test_lines_alone_replace_them():
    result = library().with_settings(lines={Weight.NORMAL: 0.3, Weight.THICK: 0.6})
    assert dict(result.lines) == {Weight.NORMAL: 0.3, Weight.THICK: 0.6}


def test_a_wire_weight_with_no_width_raises_naming_it():
    with pytest.raises(InvalidValueError, match="'thick' has no width"):
        library().with_settings(lines={Weight.NORMAL: 0.3})


@pytest.mark.parametrize("bad", [{Weight.THICK: 0}, {"thick": 0.5}, {Weight.THICK: "x"}])
def test_bad_lines_raise(bad):
    with pytest.raises(InvalidValueError):
        library().with_settings(lines=bad)


def boxed(number, width=2.2):
    """A symbol: a rectangle `width` by 1.5 M with the fixed text AAAA, 1 M tall, in its middle."""
    rect = Polyline(
        (Point(0, 0), Point(width, 0), Point(width, 1.5), Point(0, 1.5), Point(0, 0)),
    )
    text = Text("AAAA", Point(width / 2, 0.75), 1)
    return Symbol("t", SymbolKind.SYMBOL, Status.UNVERIFIED, Reference("X", number), (rect, text))


def test_a_font_that_outgrows_the_body_raises_naming_the_symbol_and_the_overflow():
    base = library(boxed("S1"), boxed("S2", 9.0), font=FONT)
    assert base.with_settings() == base
    with pytest.raises(InvalidValueError) as raised:
        base.with_settings(font=(REGULAR, BOLD))
    message = str(raised.value)
    assert "symbol S1" in message
    assert "S2" not in message
    assert "mm; shorten the text" in message


def test_a_text_anchored_outside_the_body_is_not_checked():
    beside = replace(
        boxed("S1"), elements=(*boxed("S1").elements[:1], Text("A" * 40, Point(20, 0.75), 1))
    )
    library(beside, font=FONT).with_settings(font=(REGULAR, BOLD))
