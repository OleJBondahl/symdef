"""`stretch`: every point beyond a cut line moves; offsets place ports; the result is plain."""

from dataclasses import replace

import pytest
from roundtrip import round_trips

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.geometry import (
    Arc,
    Circle,
    Direction,
    Line,
    Orientation,
    Point,
    Polyline,
    Text,
)
from symdef.load import parse_toml, symbol_from_data, validate
from symdef.model import Path, Port, Reference, Slot, Status, Stretch, Symbol, SymbolKind
from symdef.orient import orient, translate
from symdef.repeat import repeat
from symdef.serialize import symbol_to_data
from symdef.stretch import crosses_cut, stretch

N, E, S, W = Direction.N, Direction.E, Direction.S, Direction.W
PORT_X = {"1": 4, "2": 12, "3": 20, "4": 28}
SPAN = Line(Point(0, 0), Point(32, 0))
OFFSETS = {"1": 8, "2": 40, "3": 64, "4": 104}


def card() -> Symbol:
    """A PLC card: a 32 wide body, cut at x = 16, four channels on the S edge."""
    return Symbol(
        name="card",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(
            Polyline((Point(0, 0), Point(32, 0), Point(32, 8), Point(0, 8)), closed=True),
            *(Line(Point(x, 8), Point(x, 10), port=pid) for pid, x in PORT_X.items()),
        ),
        ports=tuple(Port(pid, Point(x, 10), S) for pid, x in PORT_X.items()),
        slots=(
            Slot("tag", Point(2, 2), E, (4, 1)),
            *(Slot(f"marking.{pid}", Point(x, 12), S, (3, 1)) for pid, x in PORT_X.items()),
        ),
        stretch=(Stretch("x", 16),),
    )


def by_id(items):
    return {i.id: i for i in items}


def test_the_card_stretches_to_the_requested_width_and_the_offset_ports():
    wide = stretch(card(), "x", 112, OFFSETS)
    assert body_box(wide).width == 112
    assert {p.id: p.position.x for p in wide.ports} == OFFSETS
    assert {p.id: p.position.y for p in wide.ports} == dict.fromkeys(OFFSETS, 10)
    assert all(p.direction is S for p in wide.ports)


def test_an_offset_port_takes_its_lead_and_its_marking_slot_along():
    wide = stretch(card(), "x", 112, OFFSETS)
    slots = by_id(wide.slots)
    leads = {e.port: e for e in wide.elements if isinstance(e, Line) and e.port}
    for pid, x in OFFSETS.items():
        assert slots[f"marking.{pid}"].position == Point(x, 12)
        assert (leads[pid].start, leads[pid].end) == (Point(x, 8), Point(x, 10))
    assert slots["tag"].position == Point(2, 2)


def test_without_offsets_the_points_beyond_the_cut_move_by_the_delta():
    wide = stretch(card(), "x", 112)
    assert {p.id: p.position.x for p in wide.ports} == {"1": 4, "2": 12, "3": 100, "4": 108}
    assert by_id(wide.slots)["marking.4"].position.x == 108


def test_the_result_has_no_stretch_on_that_axis_and_keeps_the_other():
    both = replace(card(), stretch=(Stretch("x", 16), Stretch("y", 4)))
    assert stretch(both, "x", 40).stretch == (Stretch("y", 4),)
    assert stretch(card(), "x", 40).stretch == ()


def test_a_line_across_the_cut_gets_longer_and_one_left_of_it_does_not_move():
    symbol = replace(
        card(),
        elements=(Line(Point(0, 0), Point(32, 0)), Line(Point(0, 1), Point(8, 1))),
        ports=(),
        slots=(),
    )
    out = stretch(symbol, "x", 48).elements
    assert out[0] == Line(Point(0, 0), Point(48, 0))
    assert out[1] == Line(Point(0, 1), Point(8, 1))


def test_a_polyline_across_the_cut_moves_only_its_points_beyond_it():
    symbol = replace(card(), elements=(Polyline((Point(0, 0), Point(16, 0), Point(32, 4))),))
    out = stretch(symbol, "x", 40, None).elements
    assert out == (Polyline((Point(0, 0), Point(16, 0), Point(40, 4))),)


def test_a_shape_wholly_beyond_the_cut_moves_whole():
    right = (SPAN, Circle(Point(24, 4), 2), Arc(Point(24, 4), 2, 0, 90), Text("abc", Point(24, 4)))
    out = stretch(replace(card(), elements=right, ports=(), slots=()), "x", 40).elements
    assert out[1:] == (
        Circle(Point(32, 4), 2),
        Arc(Point(32, 4), 2, 0, 90),
        Text("abc", Point(32, 4)),
    )


def test_a_shape_wholly_left_of_the_cut_stays():
    left = Circle(Point(4, 4), 2)
    out = stretch(replace(card(), elements=(SPAN, left), ports=(), slots=()), "x", 40).elements
    assert out[1] == left


@pytest.mark.parametrize(
    "shape", [Circle(Point(16, 4), 2), Arc(Point(16, 4), 2, 0, 360), Text("abcd", Point(16, 4))]
)
def test_a_circle_arc_or_text_across_the_cut_raises(shape):
    assert crosses_cut(shape, "x", 16)
    with pytest.raises(InvalidValueError, match="crosses the cut"):
        stretch(replace(card(), elements=(shape,), ports=(), slots=()), "x", 40)


def test_a_shape_touching_the_cut_from_one_side_is_not_across_it():
    assert not crosses_cut(Circle(Point(14, 4), 2), "x", 16)
    assert not crosses_cut(Circle(Point(18, 4), 2), "x", 16)
    assert not crosses_cut(Line(Point(0, 0), Point(32, 0)), "x", 16)


def test_a_length_below_the_natural_extent_raises():
    with pytest.raises(InvalidValueError, match="below the natural extent"):
        stretch(card(), "x", 31)


def test_a_symbol_without_a_stretch_on_the_axis_raises():
    with pytest.raises(InvalidValueError, match="no stretch on the y axis"):
        stretch(card(), "y", 40)


@pytest.mark.parametrize(
    ("offsets", "message"),
    [
        ({"1": 41}, "outside the stretched body"),
        ({"1": -1}, "outside the stretched body"),
        ({"1": 4.5}, "off the 1 M wiring grid"),
        ({"9": 4}, "does not have"),
    ],
)
def test_a_bad_offset_raises(offsets, message):
    with pytest.raises(InvalidValueError, match=message):
        stretch(card(), "x", 40, offsets)


def test_a_port_on_another_edge_raises():
    side = replace(card(), ports=(Port("1", Point(0, 4), W),))
    with pytest.raises(InvalidValueError, match="not on an edge parallel"):
        stretch(side, "x", 40, {"1": 4})


def test_the_natural_length_is_a_no_op_that_still_applies_offsets_and_drops_the_stretch():
    out = stretch(card(), "x", 32, {"1": 6})
    assert out.stretch == ()
    assert by_id(out.ports)["1"].position == Point(6, 10)
    assert body_box(out) == body_box(card())


def test_a_frame_stretched_on_x_then_y_is_two_axis_with_its_label_in_the_corner():
    frame = Symbol(
        name="frame",
        kind=SymbolKind.ELEMENT,
        status=Status.UNVERIFIED,
        reference=Reference("X", "2"),
        elements=(Polyline((Point(0, 0), Point(8, 0), Point(8, 8), Point(0, 8)), closed=True),),
        slots=(Slot("label", Point(1, 1), E, (4, 1)),),
        stretch=(Stretch("x", 4), Stretch("y", 4)),
    )
    box = body_box(stretch(stretch(frame, "x", 120), "y", 80))
    assert (box.width, box.height) == (120, 80)
    done = stretch(stretch(frame, "x", 120), "y", 80)
    assert by_id(done.slots)["label"].position == Point(1, 1)
    one_axis = body_box(stretch(frame, "x", 120))
    assert one_axis.height == 8


def test_orient_translate_and_repeat_leave_the_stretch_field_untouched():
    symbol = replace(
        card(),
        ports=(Port("in", Point(0, -2), N), Port("out", Point(0, 2), S)),
        paths=(Path("in", "out", "conductor", through=True),),
    )
    assert orient(symbol, Orientation.R90).stretch == symbol.stretch
    assert translate(symbol, 2, 2).stretch == symbol.stretch
    assert repeat(symbol, 2, port_format="{k}.{port}").stretch == symbol.stretch


TOML = """\
schema = 1
name = "Stretchable"
kind = "symbol"
status = "unverified"
reference = { standard = "IEC 60617", number = "S00001" }
stretch = [{ axis = "x", at = 1.5 }, { axis = "y", at = 0 }]
elements = [{ line = [[0, -2], [0, 2]] }]

[slots]
"""


def test_a_stretch_table_loads_validates_and_round_trips_through_resolved_data():
    data, findings = parse_toml(TOML)
    assert data is not None
    assert findings == ()
    assert validate(data) == ()
    symbol = symbol_from_data(data)
    assert symbol.stretch == (Stretch("x", 1.5), Stretch("y", 0))
    resolved = symbol_to_data(symbol)
    assert resolved["stretch"] == [{"axis": "x", "at": 1.5}, {"axis": "y", "at": 0}]
    assert validate(resolved) == ()
    assert round_trips(symbol)


def test_a_symbol_without_a_stretch_writes_no_stretch_key():
    assert "stretch" not in symbol_to_data(replace(card(), stretch=()))


def test_a_stretch_of_an_unknown_axis_is_a_schema_finding():
    data, _ = parse_toml(TOML.replace('axis = "x"', 'axis = "z"'))
    assert any(f.location == "/stretch/0/axis" for f in validate(data))
