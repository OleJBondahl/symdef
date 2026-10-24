"""`pattern_ports`: a pattern port expands into n ports along its edge; the `pattern` key."""

import pytest
from build_symbol import plain_symbol

from symdef.boxes import body_box
from symdef.edge_pattern import pattern_ports
from symdef.errors import InvalidValueError
from symdef.geometry import Direction, Line, Point, Polyline
from symdef.lint import lint
from symdef.lint.pattern import port_pattern
from symdef.load import parse_toml, symbol_from_data, validate
from symdef.model import Node, Path, Port, Slot, Stretch
from symdef.repeat import MAX_REPEAT
from symdef.serialize import symbol_to_data, to_json
from symdef.units import DEFAULT_GRID, from_divisions

N, E, S = Direction.N, Direction.E, Direction.S
PITCH = from_divisions(DEFAULT_GRID, DEFAULT_GRID.wire_pitch)


def card(width: float, *, edge: Direction = S, flag: bool = True):
    """A body `width` long along the edge, a pattern port `p` at 1 on it, its lead and its slot.

    On an E edge the symbol is the same card turned: the long side runs along y.
    """
    if edge is E:
        corners = (Point(0, 0), Point(2, 0), Point(2, width), Point(0, width))
        at, lead, slot = Point(2, 1), Line(Point(2, 1), Point(3, 1), port="p"), Point(3, 1)
    else:
        corners = (Point(0, 0), Point(width, 0), Point(width, 2), Point(0, 2))
        at, lead, slot = Point(1, 2), Line(Point(1, 2), Point(1, 3), port="p"), Point(1, 3)
    return plain_symbol(
        name="card",
        elements=(Polyline(corners, closed=True), lead),
        ports=(Port("top", Point(0, 0), N), Port("p", at, edge, "pole", flag)),
        slots=(Slot("marking.p", slot, edge, (1, 1)), Slot("tag", Point(0, 0), N, (1, 1))),
        stretch=(Stretch("y" if edge is E else "x", 1),),
    )


def wide(n: int) -> float:
    """The body length along the edge that just holds n copies."""
    return 1 + (n - 1) * PITCH


@pytest.mark.parametrize("n", [1, 2, 3, MAX_REPEAT])
def test_n_copies_stand_on_the_pitch_with_their_leads_and_marking_slots(n):
    out = pattern_ports(card(wide(n)), S, n, port_format="{k}.{port}")
    ids = [f"{k}.p" for k in range(1, n + 1)]
    assert [p.id for p in out.ports] == ["top", *ids]
    assert [p.position for p in out.ports[1:]] == [
        Point(1 + (k - 1) * PITCH, 2) for k in range(1, n + 1)
    ]
    assert all(
        p.direction is S and p.description == "pole" and not p.pattern for p in out.ports[1:]
    )
    leads = [e for e in out.elements if isinstance(e, Line)]
    assert [(e.port, e.start, e.end) for e in leads] == [
        (i, Point(1 + k * PITCH, 2), Point(1 + k * PITCH, 3)) for k, i in enumerate(ids)
    ]
    assert [s.id for s in out.slots] == [*(f"marking.{i}" for i in ids), "tag"]
    assert [s.position for s in out.slots[:n]] == [Point(1 + k * PITCH, 3) for k in range(n)]
    assert len(out.ports) == n + 1
    assert "p" not in {p.id for p in out.ports}
    assert "marking.p" not in {s.id for s in out.slots}


def test_the_other_elements_and_slots_stay_as_they_were():
    source = card(wide(3))
    out = pattern_ports(source, S, 3, port_format="{k}.{port}")
    assert out.elements[0] == source.elements[0]
    assert out.slots[-1] == source.slots[-1]
    assert out.ports[0] == source.ports[0]


def test_an_east_edge_expands_along_y():
    out = pattern_ports(card(wide(3), edge=E), E, 3, port_format="{k}.{port}")
    assert [(p.id, p.position) for p in out.ports[1:]] == [
        (f"{k}.p", Point(2, 1 + (k - 1) * PITCH)) for k in (1, 2, 3)
    ]
    assert [s.position for s in out.slots[:3]] == [Point(3, 1 + k * PITCH) for k in range(3)]


@pytest.mark.parametrize("n", [0, MAX_REPEAT + 1])
def test_n_out_of_range_raises(n):
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(3)), S, n, port_format="{k}.{port}")
    assert str(raised.value) == (
        f"card: edge S cannot carry n={n} pattern ports; ask for 1 to {MAX_REPEAT}"
    )


def test_an_edge_without_a_pattern_port_raises():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(3)), N, 2, port_format="{k}.{port}")
    assert str(raised.value) == (
        "card: declares no pattern port on edge N; set pattern = true on one port of that edge"
    )


def test_a_body_too_short_for_the_copies_raises():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(2)), S, 3, port_format="{k}.{port}")
    assert str(raised.value) == (
        f"card: 3 copies of the pattern port 'p' on edge S need a body extent of at least "
        f"{1 + 2 * PITCH:g} along the x axis; stretch it first (stretch_to_ports)"
    )
    assert body_box(card(wide(2))).width == wide(2)


def test_the_flag_is_loaded_from_toml_and_defaults_to_false():
    text = (
        'schema = 1\nname = "t"\nkind = "element"\nstatus = "unverified"\n'
        'reference = { standard = "X", number = "S00001" }\n'
        'ports = [{ id = "a", at = [0, 0], dir = "S", pattern = true }, '
        '{ id = "b", at = [2, 0], dir = "N" }]\n'
        "elements = [{ line = [[0, 0], [2, 0]] }]\n"
    )
    data, found = parse_toml(text)
    assert not found
    assert data is not None
    assert not validate(data)
    assert [p.pattern for p in symbol_from_data(data).ports] == [True, False]


def test_the_key_round_trips_and_is_absent_when_false():
    source = card(wide(2))
    data = symbol_to_data(source)
    assert [p.get("pattern") for p in data["ports"]] == [None, True]
    assert not validate(data)
    assert symbol_from_data(data).ports == source.ports
    assert '"pattern"' not in to_json(symbol_to_data(card(wide(2), flag=False)))
    assert '"pattern": true' in to_json(data)


def test_a_clean_pattern_symbol_has_no_port_pattern_finding():
    source = card(wide(2))
    assert port_pattern(source) == ()
    assert "port-pattern" not in {f.rule for f in lint(source)}


def test_a_pattern_port_is_not_reported_isolated_but_the_same_port_without_the_flag_is():
    def isolated(symbol):
        return [f.location for f in lint(symbol) if f.rule == "port-isolated"]

    assert isolated(card(wide(2))) == ["ports[0]"]
    assert isolated(card(wide(2), flag=False)) == ["ports[0]", "ports[1]"]


def test_a_second_pattern_port_on_the_edge_is_reported():
    source = card(wide(2))
    other = Port("q", Point(2, 2), S, pattern=True)
    first, second = port_pattern(
        plain_symbol(**{**vars_of(source), "ports": (*source.ports, other)})
    )
    assert (first.location, second.location) == ("ports[1]", "ports[2]")
    assert first.message == (
        "the pattern port 'p' shares edge S with the pattern port 'q'; "
        "keep one pattern port per edge"
    )
    assert second.message.startswith("the pattern port 'q' shares edge S with the pattern port 'p'")


def test_a_pattern_port_with_named_neighbours_on_its_edge_is_clean():
    source = card(wide(2))
    named = (Port("q", Point(2, 2), S), Port("r", Point(0, 2), S))
    out = plain_symbol(**{**vars_of(source), "ports": (*source.ports, *named)})
    assert port_pattern(out) == ()


def test_a_pattern_port_without_a_cut_on_its_axis_is_reported():
    source = card(wide(2))
    (finding,) = port_pattern(plain_symbol(**{**vars_of(source), "stretch": (Stretch("y", 1),)}))
    assert finding.location == "ports[1]"
    assert finding.message == (
        "the pattern port 'p' on edge S needs a stretch cut on the x axis; "
        "declare one so the edge can grow"
    )


@pytest.mark.parametrize(
    "wiring", [{"nodes": (Node(("p", "top")),)}, {"paths": (Path("top", "p", "conductor"),)}]
)
def test_a_pattern_port_named_in_a_node_or_path_is_reported(wiring):
    source = card(wide(2))
    (finding,) = port_pattern(plain_symbol(**{**vars_of(source), **wiring}))
    assert finding.location == "ports[1]"
    assert finding.message == (
        "the pattern port 'p' is named in a node or a path; "
        "leave it out, as its copies are numbered after expansion"
    )


def test_a_pattern_port_in_a_two_port_node_is_refused_with_its_text():
    source = card(wide(2))
    (finding,) = port_pattern(plain_symbol(**{**vars_of(source), "nodes": (Node(("p", "top")),)}))
    assert finding.message == (
        "the pattern port 'p' is named in a node or a path; "
        "leave it out, as its copies are numbered after expansion"
    )


def test_a_built_then_reloaded_symbol_with_one_pattern_port_per_edge_is_clean():
    data = symbol_to_data(card(wide(2)))
    assert {"ports": ["p"]} in data["nodes"]
    assert port_pattern(symbol_from_data(data)) == ()


def vars_of(symbol) -> dict:
    """The symbol's fields as keywords."""
    return {name: getattr(symbol, name) for name in symbol.__slots__}


def spans(out, edge_ids):
    """The (id, coordinate along x) of the ports with these ids."""
    return [(p.id, p.position.x) for p in out.ports if p.id in edge_ids]


@pytest.mark.parametrize("n", [1, 3, MAX_REPEAT])
def test_a_double_pitch_spaces_the_copies_two_wire_pitches_apart(n):
    out = pattern_ports(
        card(1 + (n - 1) * 2 * PITCH), S, n, pitch=2 * PITCH, port_format="{k}.{port}"
    )
    ports = [p for p in out.ports if p.id != "top"]
    assert [p.id for p in ports] == [f"{k}.p" for k in range(1, n + 1)]
    assert [p.position.x for p in ports] == [1 + k * 2 * PITCH for k in range(n)]
    leads = [e for e in out.elements if isinstance(e, Line)]
    assert [e.start.x for e in leads] == [p.position.x for p in ports]
    assert [s.position.x for s in out.slots[:n]] == [p.position.x for p in ports]


def test_positions_place_each_copy_with_its_lead_and_slot():
    coords = [0.5, 0.5 + PITCH, 0.5 + 3 * PITCH]
    out = pattern_ports(card(wide(4)), S, 3, positions=coords, port_format="{k}.{port}")
    ports = [p for p in out.ports if p.id != "top"]
    assert [p.position.x for p in ports] == coords
    assert [e.start.x for e in out.elements if isinstance(e, Line)] == coords
    assert [s.position.x for s in out.slots[:3]] == coords


def test_a_pitch_that_is_not_a_whole_multiple_raises():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(3)), S, 2, pitch=1.5 * PITCH, port_format="{k}.{port}")
    assert str(raised.value) == (
        f"card: the pitch {1.5 * PITCH:g} is not a whole multiple of the wire pitch {PITCH:g}; "
        f"use {PITCH:g}, {2 * PITCH:g}, {3 * PITCH:g} and so on"
    )


def test_a_pitch_below_the_wire_pitch_raises():
    with pytest.raises(InvalidValueError, match="is not a whole multiple of the wire pitch"):
        pattern_ports(card(wide(3)), S, 2, pitch=PITCH / 2, port_format="{k}.{port}")


def test_pitch_with_positions_raises():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(
            card(wide(3)), S, 2, pitch=PITCH, positions=[1, 1 + PITCH], port_format="{k}.{port}"
        )
    assert str(raised.value) == "card: gives both pitch and positions; give one of them"


def test_positions_of_the_wrong_length_raise():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(3)), S, 3, positions=[1, 1 + PITCH], port_format="{k}.{port}")
    assert str(raised.value) == "card: positions holds 2 coordinates for n=3 copies; give exactly 3"


def test_positions_that_do_not_increase_raise():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(3)), S, 2, positions=[1 + PITCH, 1], port_format="{k}.{port}")
    assert str(raised.value) == (
        f"card: positions {[1 + PITCH, 1]!r} do not increase; "
        f"list the copies from low to high along the edge"
    )


def test_a_position_gap_that_is_not_a_whole_multiple_raises():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(
            card(wide(3)), S, 2, positions=[0.5, 0.5 + 1.5 * PITCH], port_format="{k}.{port}"
        )
    assert str(raised.value) == (
        f"card: the gap between positions {1.5 * PITCH:g} is not a whole multiple of the wire "
        f"pitch {PITCH:g}; use {PITCH:g}, {2 * PITCH:g}, {3 * PITCH:g} and so on"
    )


def test_positions_past_the_high_side_raise():
    with pytest.raises(InvalidValueError, match="stretch it first"):
        pattern_ports(card(wide(2)), S, 2, positions=[1, 1 + 4 * PITCH], port_format="{k}.{port}")


def test_positions_before_the_low_side_raise():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(3)), S, 2, positions=[-1, -1 + PITCH], port_format="{k}.{port}")
    assert str(raised.value) == (
        "card: the first copy of the pattern port 'p' on edge S lies at -1, "
        "before the body's low side 0 along the x axis; move it inside"
    )


def mixed(width: float):
    """The card with named ports 'plus' left of 'p' and 'sig' right of it, on the same edge."""
    source = card(width)
    named = (
        Port("plus", Point(1 - PITCH, 2), S),
        Port("sig", Point(1 + PITCH, 2), S),
    )
    return plain_symbol(**{**vars_of(source), "ports": (*source.ports, *named)})


def test_copies_clear_of_the_named_ports_leave_them_untouched():
    out = pattern_ports(mixed(wide(2)), S, 1, port_format="{k}.{port}")
    assert spans(out, {"plus", "sig", "1.p"}) == [
        ("1.p", 1),
        ("plus", 1 - PITCH),
        ("sig", 1 + PITCH),
    ]


def test_a_copy_within_one_wire_pitch_of_a_named_port_raises():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(mixed(wide(3)), S, 2, port_format="{k}.{port}")
    assert str(raised.value) == (
        f"card: the copy '2.p' at {1 + PITCH:g} lies within one wire pitch {PITCH:g} "
        f"of the port 'sig' at {1 + PITCH:g} on edge S; move the port or the copy"
    )


def test_pattern_ports_reads_the_given_port_format():
    out = pattern_ports(card(wide(2)), S, 2, port_format="P{k}_{port}")
    assert [p.id for p in out.ports] == ["top", "P1_p", "P2_p"]
    assert [s.id for s in out.slots] == ["marking.P1_p", "marking.P2_p", "tag"]
    assert [e.port for e in out.elements if isinstance(e, Line)] == ["P1_p", "P2_p"]


def test_pattern_ports_refuses_a_format_without_its_fields():
    with pytest.raises(InvalidValueError, match="port_format"):
        pattern_ports(card(wide(2)), S, 2, port_format="{k}")
