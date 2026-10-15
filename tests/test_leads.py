"""`leads`: the bound leads of unlisted ports go; everything else stays, in order."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from symdef.geometry import Direction, Line, Point, Text
from symdef.leads import leads
from symdef.model import Port, Reference, Status, Symbol, SymbolKind
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
    with pytest.raises(KeyError, match="nope"):
        leads(device(), ("a", "nope"))


@given(st.sets(st.sampled_from(["a", "b"])))
def test_the_result_is_a_subsequence_and_idempotent(wired):
    source = device()
    once = leads(source, wired)
    it = iter(source.elements)
    assert all(any(e == s for s in it) for e in once.elements)
    assert leads(once, wired) == once
