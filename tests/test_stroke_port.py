"""A `Polyline` or `Arc` binds a port like a `Line`: in the file, stretch, pattern and repeat."""

from dataclasses import replace

import pytest
from build_symbol import plain_symbol
from roundtrip import round_trips

from symdef.edge_pattern import pattern_ports
from symdef.geometry import Arc, Circle, Direction, Point, Polyline, bound_port
from symdef.load import symbol_from_data, validate
from symdef.model import Port, Slot, Stretch
from symdef.repeat import repeat
from symdef.serialize import symbol_to_data
from symdef.stretch import stretch

S = Direction.S
POLY = Polyline((Point(1, 2), Point(2, 3), Point(2, 4)), port="p")


def test_a_polyline_and_an_arc_with_a_port_round_trip_through_the_file():
    sym = plain_symbol(
        elements=(POLY, Arc(Point(0, 0), 1, 0, 90, port="q")),
        ports=(Port("p", Point(2, 4), S), Port("q", Point(1, 0), S)),
    )
    assert round_trips(sym)
    assert symbol_to_data(sym)["elements"][0]["port"] == "p"
    assert symbol_from_data(symbol_to_data(sym)).elements == sym.elements


def test_the_source_key_port_is_accepted_on_polyline_and_arc_and_refused_on_circle():
    def findings(element):
        data = {
            "schema": 1,
            "name": "x",
            "kind": "symbol",
            "status": "unverified",
            "reference": {"standard": "Example set", "number": "sym-a"},
            "elements": [element],
            "slots": {},
        }
        return validate(data)

    assert findings({"polyline": [[0, 0], [1, 1]], "port": "p"}) == ()
    assert findings({"arc": [0, 0], "r": 1, "start": 0, "end": 90, "port": "p"}) == ()
    assert findings({"circle": [0, 0], "r": 1, "port": "p"}) != ()


def test_a_circle_has_no_port_field():
    with pytest.raises(TypeError):
        Circle(Point(0, 0), 1, port="p")  # ty: ignore[unknown-argument] the field must not exist


def test_stretch_moves_a_bound_polyline_with_its_offset_port():
    sym = plain_symbol(
        elements=(
            Polyline((Point(0, 0), Point(8, 0), Point(8, 2), Point(0, 2)), closed=True),
            POLY,
        ),
        ports=(Port("p", Point(2, 4), S),),
        slots=(Slot("marking.p", Point(2, 5), S, (1, 1)),),
        stretch=(Stretch("x", 4),),
    )
    out = stretch(sym, "x", 12, {"p": 6})
    assert out.elements[1] == Polyline((Point(5, 2), Point(6, 3), Point(6, 4)), port="p")


def test_repeat_renames_a_bound_polyline_per_pole():
    sym = plain_symbol(elements=(POLY,), ports=(Port("p", Point(2, 4), S),))
    out = repeat(sym, 2, port_format="{k}.{port}")
    assert [bound_port(e) for e in out.elements] == ["1.p", "2.p"]


def test_edge_pattern_copies_a_bound_polyline_per_pole():
    sym = plain_symbol(
        elements=(
            Polyline((Point(0, 0), Point(40, 0), Point(40, 2), Point(0, 2)), closed=True),
            POLY,
        ),
        ports=(Port("p", Point(1, 2), S, "pole", pattern=True),),
        slots=(Slot("marking.p", Point(1, 3), S, (1, 1)),),
        stretch=(Stretch("x", 1),),
    )
    sym = replace(sym, elements=(sym.elements[0], replace(POLY, points=(Point(1, 2), Point(1, 3)))))
    out = pattern_ports(sym, S, 2, port_format="{k}.{port}")
    bound = [e for e in out.elements if isinstance(e, Polyline) and e.port]
    assert [e.port for e in bound] == ["1.p", "2.p"]
    assert (
        bound[1].points[0].x - bound[0].points[0].x
        == out.ports[1].position.x - out.ports[0].position.x
    )
