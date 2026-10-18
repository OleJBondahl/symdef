"""`leads`: the bound leads of unlisted ports go; everything else stays, in order."""

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from symdef.boxes import keepout_box
from symdef.errors import UnknownNameError
from symdef.geometry import Box, Direction, Line, Point, Text
from symdef.leads import leads, only_ports
from symdef.model import Port, Reference, Slot, Status, Stretch, Symbol, SymbolKind
from symdef.stretch import stretch
from symdef.table import table

S = Direction.S
LEAD_A = Line(Point(0, 0), Point(0, 2), port="a")
LEAD_B = Line(Point(4, 0), Point(4, 2), port="b")
BODY = Line(Point(0, 0), Point(4, 0))
LABEL = Text("x", Point(2, 3))


def device() -> Symbol:
    return Symbol(
        name="d",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(LEAD_A, BODY, LEAD_B, LABEL),
        ports=(Port("a", Point(0, 2), S), Port("b", Point(4, 2), S)),
    )


def test_a_listed_port_keeps_its_lead_and_unbound_elements_stay():
    assert leads(device(), ("a",)).elements == (LEAD_A, BODY, LABEL)


def test_no_ports_keeps_only_what_is_not_a_bound_lead():
    assert leads(device(), ()).elements == (BODY, LABEL)


def test_every_port_keeps_the_symbol_whole():
    assert leads(device(), ["b", "a"]) == device()


def test_other_fields_are_unchanged():
    out = leads(device(), ())
    assert (out.ports, out.name, out.slots) == (device().ports, "d", ())


def test_a_table_row_is_named_by_its_prefixed_id():
    two = table(device(), 2, "y")
    kept = leads(two, ("1.a",))
    assert [e.port for e in kept.elements if isinstance(e, Line) and e.port] == ["1.a"]


def test_an_unknown_id_raises_key_error_naming_it():
    with pytest.raises(UnknownNameError, match="nope"):
        leads(device(), ("a", "nope"))


@given(st.sets(st.sampled_from(["a", "b"])))
def test_the_result_is_a_subsequence_and_idempotent(wired):
    source = device()
    once = leads(source, wired)
    it = iter(source.elements)
    assert all(any(e == s for s in it) for e in once.elements)
    assert leads(once, wired) == once


def seven() -> Symbol:
    """A body 0..8 wide with seven bottom ports at x 1..7, each with a lead and a marking slot."""
    ids = [str(i) for i in range(1, 8)]
    return Symbol(
        name="seven",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(
            Line(Point(0, 0), Point(8, 0)),
            *(Line(Point(int(i), 0), Point(int(i), 1), port=i) for i in ids),
        ),
        ports=tuple(Port(i, Point(int(i), 1), S) for i in ids),
        slots=(
            Slot("tag", Point(-9, 0), Direction.W, (6, 1)),
            *(Slot(f"marking.{i}", Point(int(i) + 0.25, 1), Direction.S, (1.5, 1)) for i in ids),
        ),
        stretch=(Stretch("x", 4),),
    )


def test_only_ports_keeps_the_listed_ports_their_leads_and_marking_slots():
    out = only_ports(seven(), ("3", "5"))
    assert [p.id for p in out.ports] == ["3", "5"]
    assert [e.port for e in out.elements if isinstance(e, Line) and e.port] == ["3", "5"]
    assert [s.id for s in out.slots] == ["tag", "marking.3", "marking.5"]
    assert out.stretch == seven().stretch


def test_only_ports_shrinks_the_keepout_to_the_bound_extent():
    declared = replace(seven(), body=Box(Point(2, -1), Point(6, 0)))
    assert keepout_box(declared) == Box(Point(1, -1), Point(7, 1))
    assert keepout_box(only_ports(declared, ("3", "5"))) == Box(Point(2, -1), Point(6, 1))


def test_only_ports_then_stretch_leaves_no_off_grid_unbound_port():
    out = stretch(only_ports(seven(), ("1", "7")), "x", 10, {"1": 1, "7": 9})
    assert {p.id: p.position.x for p in out.ports} == {"1": 1, "7": 9}
    assert all(float(s.position.x - 0.25).is_integer() for s in out.slots if s.id != "tag")
    assert len(out.slots) == 3


def test_only_ports_with_an_unknown_name_names_the_port_and_the_symbol():
    with pytest.raises(UnknownNameError, match=r"'nope'.*'seven'"):
        only_ports(seven(), ("1", "nope"))


def test_only_ports_of_a_table_row_uses_the_prefixed_id():
    kept = only_ports(table(device(), 2, "y"), ("1.a",))
    assert [p.id for p in kept.ports] == ["1.a"]
