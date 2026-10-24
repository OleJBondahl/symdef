"""`stretch_to_ports` on a pattern edge: stretch, then `pattern_ports`, n ports on the pitch."""

from dataclasses import replace

import pytest
from test_edge_pattern import PITCH, card, mixed, spans, wide

from symdef.boxes import body_box
from symdef.edge_pattern import pattern_ports
from symdef.errors import InvalidValueError
from symdef.geometry import Box, Direction, Line, Point
from symdef.model import Port, Stretch
from symdef.repeat import MAX_REPEAT
from symdef.stretch import stretch
from symdef.stretch_ports import stretch_to_ports

S, E = Direction.S, Direction.E


def cut_inside(source, axis):
    """The card with its cut inside the body, so the body grows when stretched."""
    return replace(source, stretch=(Stretch(axis, 0.5),))


def grown(source, edge, n):
    axis = "y" if edge is E else "x"
    source = cut_inside(source, axis)
    length, offsets = stretch_to_ports(source, axis, edge, n)
    return (
        length,
        offsets,
        pattern_ports(stretch(source, axis, length, offsets), edge, n, port_format="{k}.{port}"),
    )


@pytest.mark.parametrize("n", [1, 2, 3, 4, 8, MAX_REPEAT])
@pytest.mark.parametrize("declared", [False, True])
def test_the_copies_stand_on_the_pitch_inside_the_grown_body(n, declared):
    source = card(wide(1))
    if declared:
        source = replace(source, body=Box(Point(0, 0), Point(1, 2)))
    length, offsets, result = grown(source, S, n)
    assert length == wide(n)
    assert offsets == {"p": 1}
    assert body_box(result).width == length
    ports = [p for p in result.ports if p.id != "top"]
    assert [p.id for p in ports] == [f"{k}.p" for k in range(1, n + 1)]
    assert [p.position.x for p in ports] == [1 + k * PITCH for k in range(n)]
    assert [e.port for e in result.elements if isinstance(e, Line) and e.port] == [
        p.id for p in ports
    ]
    assert [s.id for s in result.slots if s.id.startswith("marking.")] == [
        f"marking.{p.id}" for p in ports
    ]


def test_an_east_pattern_edge_grows_along_y():
    length, _, result = grown(card(wide(1), edge=E), E, 3)
    assert length == wide(3)
    assert body_box(result).height == length
    assert [p.position.y for p in result.ports if p.id != "top"] == [1, 1 + PITCH, 1 + 2 * PITCH]


def test_n_above_the_bound_raises_with_the_fix():
    with pytest.raises(InvalidValueError) as raised:
        stretch_to_ports(card(wide(1)), "x", S, MAX_REPEAT + 1)
    assert str(raised.value) == (
        f"card: edge S cannot carry n={MAX_REPEAT + 1} ports; "
        f"it declares {MAX_REPEAT}; ask for 1 to {MAX_REPEAT}"
    )


@pytest.mark.parametrize("n", [1, 3, MAX_REPEAT])
def test_a_double_pitch_grows_the_body_and_places_the_copies(n):
    source = cut_inside(card(wide(1)), "x")
    length, offsets = stretch_to_ports(source, "x", S, n, pitch=2 * PITCH)
    assert length == wide(1) + (n - 1) * 2 * PITCH
    assert offsets == {"p": 1}
    result = pattern_ports(
        stretch(source, "x", length, offsets), S, n, pitch=2 * PITCH, port_format="{k}.{port}"
    )
    assert [p.position.x for p in result.ports if p.id != "top"] == [
        1 + k * 2 * PITCH for k in range(n)
    ]


def test_positions_grow_the_body_to_the_last_position():
    source = cut_inside(card(wide(1)), "x")
    coords = [2, 2 + 2 * PITCH]
    length, offsets = stretch_to_ports(source, "x", S, 2, positions=coords)
    assert (length, offsets) == (wide(1) + 1 + 2 * PITCH, {"p": 2})
    result = pattern_ports(
        stretch(source, "x", length, offsets), S, 2, positions=coords, port_format="{k}.{port}"
    )
    assert [p.position.x for p in result.ports if p.id != "top"] == coords


def test_a_bad_pitch_is_refused_on_a_pattern_edge():
    with pytest.raises(InvalidValueError, match="is not a whole multiple of the wire pitch"):
        stretch_to_ports(card(wide(1)), "x", S, 2, pitch=1.5 * PITCH)


def test_pitch_or_positions_on_a_non_pattern_edge_raise():
    source = cut_inside(card(wide(1)), "x")
    source = replace(source, ports=(*source.ports, Port("q", Point(0, 0), Direction.N)))
    for extra in ({"pitch": PITCH}, {"positions": [0]}):
        with pytest.raises(InvalidValueError) as raised:
            stretch_to_ports(source, "x", Direction.N, 1, **extra)  # ty: ignore[invalid-argument-type]  # a bad value on purpose
        assert str(raised.value) == (
            "card: pitch and positions apply to a pattern edge only; edge N has no pattern port"
        )


@pytest.mark.parametrize("n", [1, 3, MAX_REPEAT])
def test_a_mixed_edge_keeps_the_gap_from_the_last_copy_to_the_named_port(n):
    source = replace(mixed(wide(1) + 2 * PITCH), stretch=(Stretch("x", 0.5),))
    length, offsets = stretch_to_ports(source, "x", S, n)
    grow = (n - 1) * PITCH
    assert offsets == {"plus": 1 - PITCH, "p": 1, "sig": 1 + PITCH + grow}
    assert length == wide(1) + 2 * PITCH + grow
    result = pattern_ports(stretch(source, "x", length, offsets), S, n, port_format="{k}.{port}")
    xs = dict(spans(result, {f"{k}.p" for k in range(1, n + 1)} | {"plus", "sig"}))
    assert sorted(xs) == sorted([*(f"{k}.p" for k in range(1, n + 1)), "plus", "sig"])
    assert xs["plus"] == 1 - PITCH
    assert xs[f"{n}.p"] == 1 + grow
    assert xs["sig"] - xs[f"{n}.p"] == PITCH
    assert body_box(result).width == length
