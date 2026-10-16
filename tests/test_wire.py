"""Wire styles: `[[wire]]` in `library.toml`, the `wires` bundle array, and `wire()`."""

import json

import pytest

from symdef.errors import InvalidValueError, UnknownNameError
from symdef.geometry import Fill, Point, Polyline, Style, Weight
from symdef.load import library_from_bundle, parse_config, validate_bundle
from symdef.model import Finding, Library, Reference, Severity, Status, SymbolKind, WireStyle
from symdef.serialize import bundle_to_data, to_json
from symdef.wire import wire

WIRES = (
    WireStyle("link", Weight.NORMAL, Style.DASHED),
    WireStyle("trunk", Weight.THICK, Style.SOLID),
    WireStyle("wire", Weight.NORMAL, Style.SOLID),
)
LIBRARY = Library("IEC 60617", "IEC 60617", "", {}, wires=WIRES)
PATH = [(0, 0), (4, 0), (4, 6)]

CONFIG = """standard = "IEC 60617"
title = "IEC 60617 symbols"
number_pattern = '^S\\d{5}$'
"""
GOOD_WIRE = """
[[wire]]
id = "link"
weight = "normal"
style = "dashed"
"""


def polyline_of(symbol) -> Polyline:
    (element,) = symbol.elements
    assert isinstance(element, Polyline)
    return element


def test_a_wire_is_one_open_dashed_polyline_through_the_points():
    symbol = wire(LIBRARY, "link", [Point(0, 0), Point(4, 0), Point(4, 6)])
    line = polyline_of(symbol)
    assert line.points == (Point(0, 0), Point(4, 0), Point(4, 6))
    assert line.closed is False
    assert line.fill is Fill.NONE
    assert line.style is Style.DASHED
    assert line.weight is Weight.NORMAL


def test_the_style_and_weight_come_from_the_named_wire_style():
    line = polyline_of(wire(LIBRARY, "trunk", PATH))
    assert (line.weight, line.style) == (Weight.THICK, Style.SOLID)


def test_a_wire_is_an_unverified_element_with_no_ports_or_slots():
    symbol = wire(LIBRARY, "link", PATH)
    assert symbol.kind is SymbolKind.ELEMENT
    assert symbol.status is Status.UNVERIFIED
    assert symbol.name == "wire link"
    assert symbol.reference == Reference("IEC 60617", "wire.link")
    assert (symbol.ports, symbol.slots, symbol.nodes, symbol.paths, symbol.anchors) == (
        (),
        (),
        (),
        (),
        (),
    )


def test_pairs_and_points_give_the_same_wire():
    assert wire(LIBRARY, "link", PATH) == wire(
        LIBRARY, "link", [Point(0, 0), Point(4, 0), Point(4, 6)]
    )


def test_an_unknown_style_id_is_a_key_error_naming_it():
    with pytest.raises(UnknownNameError, match="no wire style 'nope' in IEC 60617"):
        wire(LIBRARY, "nope", PATH)


def test_a_wire_needs_two_points():
    with pytest.raises(InvalidValueError, match="at least 2 points, got 1"):
        wire(LIBRARY, "link", [(0, 0)])


def test_a_good_wire_table_loads():
    config, findings = parse_config(CONFIG + GOOD_WIRE)
    assert findings == ()
    assert config is not None
    assert config.wires == (WireStyle("link", Weight.NORMAL, Style.DASHED),)


def test_an_absent_wire_list_is_empty():
    config, findings = parse_config(CONFIG)
    assert findings == ()
    assert config is not None
    assert config.wires == ()


@pytest.mark.parametrize(
    ("body", "location", "message"),
    [
        ('weight = "heavy"\nstyle = "solid"\nid = "a"', "/wire/0/weight", "must be one of"),
        ('id = "a"\nweight = "normal"\nstyle = "wavy"', "/wire/0/style", "must be one of"),
        ('weight = "normal"\nstyle = "solid"', "/wire/0", "missing required key 'id'"),
        ('id = 3\nweight = "normal"\nstyle = "solid"', "/wire/0/id", "must be a string"),
    ],
)
def test_a_bad_wire_table_is_a_finding(body, location, message):
    config, findings = parse_config(CONFIG + f"\n[[wire]]\n{body}\n")
    assert config is None
    assert len(findings) == 1
    assert (findings[0].rule, findings[0].location) == ("schema", location)
    assert message in findings[0].message


def test_a_wire_entry_that_is_not_a_table_is_a_finding():
    config, findings = parse_config(CONFIG + "wire = [1]\n")
    assert config is None
    assert [f.location for f in findings] == ["/wire/0"]


def test_a_duplicate_wire_id_is_a_finding():
    config, findings = parse_config(CONFIG + GOOD_WIRE + GOOD_WIRE)
    assert config is None
    assert findings == (
        Finding("schema", Severity.ERROR, "duplicate wire id 'link'", location="/wire"),
    )


def test_a_library_with_wires_round_trips_through_the_bundle():
    data = json.loads(to_json(bundle_to_data(LIBRARY)))
    assert data["wires"][0] == {"id": "link", "weight": "normal", "style": "dashed"}
    assert validate_bundle(data) == ()
    assert library_from_bundle(data).wires == WIRES


def test_a_bundle_without_wires_has_no_wires_key():
    data = bundle_to_data(Library("IEC 60617", "IEC 60617", "", {}))
    assert "wires" not in data
    assert library_from_bundle(data).wires == ()


def test_bad_bundle_wire_entries_are_findings():
    data = {
        "schema": 1,
        "standard": "IEC 60617",
        "symbols": {},
        "wires": [{"id": "a", "weight": "heavy", "style": "solid"}, 4],
    }
    found = validate_bundle(data)
    assert {f.location for f in found} == {"/wires/0/weight", "/wires/1"}
