"""`table`: rows along an axis, ports and every slot prefixed, a head placed as authored."""

from dataclasses import replace

import pytest

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.geometry import Direction, Line, Point, Style, Weight
from symdef.model import Path, Port, Reference, Slot, Status, Stretch, Symbol, SymbolKind
from symdef.table import table

N, E, S, W = Direction.N, Direction.E, Direction.S, Direction.W


def row(**fields) -> Symbol:
    """A row two units high and four wide, with a lead to port `in` and a marking slot."""
    base = Symbol(
        name="row",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(
            Line(Point(0, -1), Point(4, -1), Weight.NORMAL, Style.SOLID),
            Line(Point(0, 1), Point(4, 1), Weight.NORMAL, Style.SOLID),
            Line(Point(-2, 0), Point(0, 0), Weight.NORMAL, Style.SOLID, port="in"),
        ),
        ports=(Port("in", Point(-2, 0), W), Port("out", Point(4, 0), E)),
        paths=(Path("in", "out", "conductor", through=True),),
        slots=(Slot("marking.in", Point(-2, 0), W, (1, 1)), Slot("x", Point(2, 0), N, (1, 1))),
    )
    return replace(base, **fields)


def head(*elements: Line, **fields) -> Symbol:
    """A head with port `h` and slot `hs`, drawn as the given lines."""
    base = Symbol(
        name="head",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "2"),
        elements=elements,
        ports=(Port("h", Point(0, 0), N),),
        slots=(Slot("hs", Point(0, 0), N, (1, 1)),),
    )
    return replace(base, **fields)


def test_rows_are_prefixed_and_stacked_on_y_after_the_head():
    r = row()
    h = head(Line(Point(0, 5), Point(1, 5), Weight.NORMAL, Style.SOLID))
    t = table(r, 3, "y", h, port_format="{k}.{port}")
    step = body_box(r).height
    assert t.elements[: len(h.elements)] == h.elements
    assert [s.id for s in t.slots] == [
        "hs",
        "marking.1.in",
        "1.x",
        "marking.2.in",
        "2.x",
        "marking.3.in",
        "3.x",
    ]
    assert [p.id for p in t.ports] == ["h", "1.in", "1.out", "2.in", "2.out", "3.in", "3.out"]
    ports = {p.id: p for p in t.ports}
    assert ports["1.in"].position == Point(-2, 0)
    assert ports["3.in"].position.y == pytest.approx(2 * step)
    assert [e.port for e in t.elements if isinstance(e, Line) and e.port is not None] == [
        "1.in",
        "2.in",
        "3.in",
    ]


def test_a_head_with_a_stretch_on_the_axis_spans_the_rows():
    r = row()
    h = head(
        Line(Point(0, 0), Point(2, 0), Weight.NORMAL, Style.SOLID),
        stretch=(Stretch("x", 1),),
    )
    t = table(r, 4, "x", h, port_format="{k}.{port}")
    step = body_box(r).width
    head_part = replace(t, elements=t.elements[:1])
    assert body_box(head_part).width == pytest.approx(4 * step)
    assert t.stretch == ()


def test_a_head_without_a_stretch_is_untouched():
    h = head(Line(Point(0, 0), Point(2, 0), Weight.NORMAL, Style.SOLID))
    t = table(row(), 4, "x", h, port_format="{k}.{port}")
    assert t.elements[: len(h.elements)] == h.elements
    assert body_box(replace(t, elements=t.elements[:1])).width == body_box(h).width


def test_a_head_stretch_on_the_other_axis_is_not_applied():
    h = head(
        Line(Point(0, 0), Point(2, 0), Weight.NORMAL, Style.SOLID),
        stretch=(Stretch("y", 1),),
    )
    t = table(row(), 4, "x", h, port_format="{k}.{port}")
    assert t.elements[: len(h.elements)] == h.elements


def test_a_stretched_head_keeps_its_authored_place_relative_to_row_one():
    h = head(
        Line(Point(0, -3), Point(2, -3), Weight.NORMAL, Style.SOLID),
        stretch=(Stretch("x", 1),),
    )
    t = table(row(), 3, "x", h, port_format="{k}.{port}")
    box = body_box(replace(t, elements=t.elements[:1]))
    assert box.min == body_box(h).min
    assert box.max.y == body_box(h).max.y


def test_the_head_stretch_must_fit_the_rows():
    h = head(
        Line(Point(0, 0), Point(8, 0), Weight.NORMAL, Style.SOLID),
        stretch=(Stretch("x", 4),),
    )
    with pytest.raises(InvalidValueError, match="below the natural extent"):
        table(row(), 1, "x", h, port_format="{k}.{port}")


@pytest.mark.parametrize("n", [0, 65])
def test_the_row_count_is_bounded(n):
    with pytest.raises(InvalidValueError, match="between 1 and 64"):
        table(row(), n, "x", port_format="{k}.{port}")


def test_one_row_works():
    t = table(row(), 1, "x", port_format="{k}.{port}")
    assert [p.id for p in t.ports] == ["1.in", "1.out"]


def test_a_row_without_a_through_path_works():
    t = table(row(paths=()), 2, "x", port_format="{k}.{port}")
    assert t.paths == ()


def test_pole_pitch_is_the_rows_and_the_stretch_is_gone():
    t = table(row(pole_pitch=7), 2, "x", port_format="{k}.{port}")
    assert t.pole_pitch == 7
    assert t.stretch == ()


def test_table_reads_the_given_port_format():
    t = table(row(), 2, "x", port_format="P{k}_{port}")
    assert [p.id for p in t.ports] == ["P1_in", "P1_out", "P2_in", "P2_out"]
    assert [s.id for s in t.slots] == ["marking.P1_in", "P1_x", "marking.P2_in", "P2_x"]
    assert {e.port for e in t.elements if isinstance(e, Line) and e.port} == {"P1_in", "P2_in"}
    assert {p for n in t.nodes for p in n.ports} == {"P1_in", "P1_out", "P2_in", "P2_out"}


def test_table_refuses_a_format_without_its_fields():
    with pytest.raises(InvalidValueError, match="port_format"):
        table(row(), 2, "x", port_format="{port}")
