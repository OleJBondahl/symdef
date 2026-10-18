"""`stretch_to_ports`: the length and offsets that put n ports on the wire pitch."""

import pytest

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.geometry import Direction, Line, Point, Polyline
from symdef.leads import only_ports
from symdef.model import Port, Reference, Slot, Status, Stretch, Symbol, SymbolKind
from symdef.stretch import stretch
from symdef.stretch_ports import stretch_to_ports
from symdef.units import Grid

S, N = Direction.S, Direction.N
XS = [1 + 0.5 * i for i in range(7)]  # seven bottom ports declared 0.5 M apart: 1 .. 4


def card(*, cut: bool = True) -> Symbol:
    """A body 0..5 wide, a diagonal across the cut, seven bottom ports with leads and slots."""
    ids = [str(i) for i in range(7)]
    return Symbol(
        name="card",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(
            Polyline((Point(0, 0), Point(5, 0), Point(5, 2), Point(0, 2)), closed=True),
            Line(Point(0, 0), Point(5, 2)),
            *(Line(Point(x, 2), Point(x, 3), port=i) for i, x in zip(ids, XS, strict=True)),
        ),
        ports=(
            *(Port(i, Point(x, 3), S) for i, x in zip(ids, XS, strict=True)),
            Port("top", Point(2, -1), N),
        ),
        slots=tuple(
            Slot(f"marking.{i}", Point(x, 3), S, (1, 1)) for i, x in zip(ids, XS, strict=True)
        ),
        stretch=(Stretch("x", 2.5),) if cut else (),
    )


@pytest.mark.parametrize("n", range(2, 8))
def test_n_ports_stand_on_the_pitch_inside_the_stretched_body(n):
    length, offsets = stretch_to_ports(card(), "x", S, n)
    assert list(offsets) == [str(i) for i in range(n)]
    assert list(offsets.values()) == [1 + i for i in range(n)]
    assert length == max(5, 1 + (n - 1) + 1)
    wide = stretch(only_ports(card(), offsets), "x", length, offsets)
    assert body_box(wide).width == length
    assert [p.position.x for p in wide.ports] == list(offsets.values())
    assert all(float(p.position.x).is_integer() for p in wide.ports)


def test_the_diagonal_across_the_cut_still_ends_on_the_far_corner():
    length, offsets = stretch_to_ports(card(), "x", S, 7)
    wide = stretch(only_ports(card(), offsets), "x", length, offsets)
    diagonal = next(e for e in wide.elements if isinstance(e, Line) and e.port is None)
    assert (diagonal.start, diagonal.end) == (Point(0, 0), Point(length, 2))
    assert length == 8


def test_the_pitch_is_the_grids_wire_pitch():
    grid = Grid(wire_pitch=16)
    length, offsets = stretch_to_ports(card(), "x", S, 3, grid=grid)
    assert list(offsets.values()) == [1, 3, 5]
    assert length == 1 + 4 + 1


def test_n_above_the_declared_count_raises_naming_symbol_edge_n_and_count():
    with pytest.raises(InvalidValueError, match=r"card.*S.*n=8.*declares 7"):
        stretch_to_ports(card(), "x", S, 8)


def test_n_below_one_raises():
    with pytest.raises(InvalidValueError, match="n=0"):
        stretch_to_ports(card(), "x", S, 0)


def test_a_symbol_without_a_cut_on_the_axis_raises():
    with pytest.raises(InvalidValueError, match=r"card.*no stretch on the x axis.*S.*n=2"):
        stretch_to_ports(card(cut=False), "x", S, 2)


def test_an_edge_across_the_axis_raises():
    with pytest.raises(InvalidValueError, match="not parallel"):
        stretch_to_ports(card(), "x", Direction.E, 2)
