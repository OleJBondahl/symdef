"""`Style.DASH_DOT`: accepted wherever `dashed` is, drawn as dash, gap, dot, gap."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from neutral_font import NEUTRAL_FONT, NEUTRAL_FONT_TOML
from roundtrip import round_trips

from symdef.authoring import lint
from symdef.errors import InvalidValueError
from symdef.geometry import Arc, Line, Point, Polyline, Style, Weight
from symdef.load import parse_config, parse_toml, symbol_from_data, validate
from symdef.model import Library, LibraryConfig, Reference, Status, Symbol, SymbolKind, WireStyle
from symdef.serialize import symbol_to_data
from symdef.svg import to_fragment, to_svg
from symdef.svg_mm import to_fragment_mm
from symdef.wire import wire

SCHEMA = json.loads(
    (Path(__file__).parents[1] / "src" / "symdef" / "schema" / "symbol.schema.json").read_text(
        encoding="utf-8"
    )
)
DD = Style.DASH_DOT
ELEMENT_TOML = """
schema = 1
name = "outline"
kind = "element"
status = "unverified"
reference = { standard = "Example set", number = "sym-a" }
elements = [
  { line = [[0, 0], [4, 0]], style = "dash_dot" },
  { polyline = [[0, 0], [4, 0], [4, 4]], style = "dash_dot" },
  { arc = [2, 2], r = 1, start = 0, end = 90, style = "dash_dot" },
]
"""


def sym(*elements):
    return Symbol(
        name="t",
        kind=SymbolKind.ELEMENT,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=tuple(elements),
    )


def three():
    return sym(
        Line(Point(0, 0), Point(4, 0), style=DD),
        Polyline((Point(0, 0), Point(4, 0), Point(4, 4)), style=DD),
        Arc(Point(2, 2), 1, 0, 90, style=DD),
    )


def mm(symbol, **extra):
    return to_fragment_mm(
        symbol,
        module_mm=2.5,
        weights_mm={Weight.NORMAL: 0.25},
        dash_mm=(1.2, 0.6),
        font_family="sans-serif",
        font_mm=2.0,
        cap_ratio=0.7,
        **extra,
    )


def test_a_file_with_dash_dot_loads_lints_clean_and_round_trips():
    data, parsed = parse_toml(ELEMENT_TOML)
    assert parsed == ()
    assert validate(data) == ()
    assert data is not None
    symbol = symbol_from_data(data)
    assert symbol.elements == three().elements
    assert lint(symbol) == ()
    assert round_trips(symbol)
    assert {e["style"] for e in symbol_to_data(symbol)["elements"]} == {"dash_dot"}


def test_the_json_schema_accepts_dash_dot():
    assert Draft202012Validator(SCHEMA).is_valid(parse_toml(ELEMENT_TOML)[0])


def test_module_units_draw_the_four_number_pattern_on_every_shape():
    for out in (to_fragment(three()), to_svg(three())):
        assert out.count('stroke-dasharray="1 0.25 0.0625 0.25"') == 3


def test_millimetres_draw_the_callers_four_numbers():
    out = mm(three(), dash_dot_mm=(4, 1, 0.25, 1))
    assert out.count('stroke-dasharray="4 1 0.25 1"') == 3


def test_millimetres_without_the_keyword_raise_naming_it():
    with pytest.raises(InvalidValueError, match="dash_dot_mm"):
        mm(three())


def test_the_keyword_is_only_needed_by_a_symbol_that_uses_the_style():
    assert "dasharray" not in mm(sym(Line(Point(0, 0), Point(1, 0))))
    assert 'stroke-dasharray="1.2 0.6"' in mm(
        sym(Line(Point(0, 0), Point(1, 0), style=Style.DASHED))
    )


def test_a_wire_style_can_be_dash_dot():
    text = (
        'standard = "Example set"\ntitle = "t"\nnumber_pattern = "^S"\nport_format = "{k}.{port}"\n'
        + NEUTRAL_FONT_TOML
        + '[[wire]]\nid = "o"\n'
    )
    config, findings = parse_config(text + 'weight = "normal"\nstyle = "dash_dot"\n')
    assert findings == ()
    assert isinstance(config, LibraryConfig)
    assert config.wires == (WireStyle("o", Weight.NORMAL, DD),)
    library = Library(
        config.standard,
        config.title,
        config.number_pattern,
        {},
        wires=config.wires,
        font=NEUTRAL_FONT,
        port_format="{k}.{port}",
    )
    assert to_fragment(wire(library, "o", [(0, 0), (4, 0)])).count("1 0.25 0.0625 0.25") == 1
