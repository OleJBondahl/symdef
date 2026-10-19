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
    out = pattern_ports(card(wide(n)), S, n)
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
    out = pattern_ports(source, S, 3)
    assert out.elements[0] == source.elements[0]
    assert out.slots[-1] == source.slots[-1]
    assert out.ports[0] == source.ports[0]


def test_an_east_edge_expands_along_y():
    out = pattern_ports(card(wide(3), edge=E), E, 3)
    assert [(p.id, p.position) for p in out.ports[1:]] == [
        (f"{k}.p", Point(2, 1 + (k - 1) * PITCH)) for k in (1, 2, 3)
    ]
    assert [s.position for s in out.slots[:3]] == [Point(3, 1 + k * PITCH) for k in range(3)]


@pytest.mark.parametrize("n", [0, MAX_REPEAT + 1])
def test_n_out_of_range_raises(n):
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(3)), S, n)
    assert str(raised.value) == (
        f"card: edge S cannot carry n={n} pattern ports; ask for 1 to {MAX_REPEAT}"
    )


def test_an_edge_without_a_pattern_port_raises():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(3)), N, 2)
    assert str(raised.value) == (
        "card: declares no pattern port on edge N; set pattern = true on one port of that edge"
    )


def test_a_body_too_short_for_the_copies_raises():
    with pytest.raises(InvalidValueError) as raised:
        pattern_ports(card(wide(2)), S, 3)
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


def test_a_pattern_port_sharing_its_edge_is_reported():
    source = card(wide(2))
    other = Port("q", Point(2, 2), S)
    (finding,) = port_pattern(plain_symbol(**{**vars_of(source), "ports": (*source.ports, other)}))
    assert finding.location == "ports[1]"
    assert finding.message == (
        "the pattern port 'p' shares edge S with another port; keep it the only port on that edge"
    )


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


def vars_of(symbol) -> dict:
    """The symbol's fields as keywords."""
    return {name: getattr(symbol, name) for name in symbol.__slots__}
