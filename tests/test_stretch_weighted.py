"""Several weighted cuts per axis (D67) and slots that follow them (D69)."""

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from roundtrip import round_trips

from symdef.boxes import slot_box
from symdef.errors import InvalidValueError
from symdef.geometry import Arc, Circle, Direction, Line, Point, Text
from symdef.load import parse_toml, symbol_from_data, validate
from symdef.model import Anchor, Centre, Reference, Slot, Status, Stretch, Symbol, SymbolKind
from symdef.serialize import symbol_to_data
from symdef.stretch import stretch

N, E, S, W = Direction.N, Direction.E, Direction.S, Direction.W
CUTS = (Stretch("x", 4), Stretch("x", 8, 3))


def base(*elements, slots=(), anchors=(), cuts=CUTS) -> Symbol:
    """A 12 wide symbol with the given parts and by default the cuts of weight 1 and 3."""
    return Symbol(
        name="w",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(Line(Point(0, 0), Point(12, 0)), *elements),
        slots=slots,
        anchors=anchors,
        stretch=cuts,
    )


def test_growth_is_shared_by_weight_and_a_point_moves_by_the_shares_it_lies_beyond():
    anchors = tuple(Anchor(f"a{x}", Point(x, 0), N) for x in (2, 6, 10))
    out = stretch(base(anchors=anchors), "x", 20)  # grown by 8: shares 2 and 6
    assert [a.position.x for a in out.anchors] == [2, 8, 18]
    assert out.stretch == ()


def test_the_cuts_are_taken_in_order_of_their_place_not_of_the_file():
    anchors = (Anchor("a", Point(6, 0), N),)
    out = stretch(base(anchors=anchors, cuts=tuple(reversed(CUTS))), "x", 20)
    assert out.anchors[0].position.x == 8


def test_a_line_across_a_cut_grows_by_that_cuts_share():
    out = stretch(base(Line(Point(5, 1), Point(10, 1)), Line(Point(1, 2), Point(9, 2))), "x", 20)
    assert out.elements[1] == Line(Point(7, 1), Point(18, 1))
    assert out.elements[2] == Line(Point(1, 2), Point(17, 2))


def test_whole_shapes_move_by_the_shares_of_the_cuts_before_them():
    out = stretch(base(Circle(Point(6, 3), 1), Text("a", Point(10, 4), 1)), "x", 20)
    assert out.elements[1] == Circle(Point(8, 3), 1)
    assert out.elements[2] == Text("a", Point(18, 4), 1)


@pytest.mark.parametrize("x", [4, 8])
@pytest.mark.parametrize("cls", ["circle", "arc", "text"])
def test_a_circle_arc_or_text_across_either_cut_raises(x, cls):
    shape = {
        "circle": Circle(Point(x, 3), 1),
        "arc": Arc(Point(x, 3), 1, 0, 360),
        "text": Text("ab", Point(x - 0.5, 3), 1),
    }[cls]
    with pytest.raises(InvalidValueError, match="crosses the cut"):
        stretch(base(shape), "x", 20)


def test_a_single_cut_gives_the_whole_growth_whatever_its_weight():
    out = stretch(base(Line(Point(5, 1), Point(10, 1)), cuts=(Stretch("x", 4, 7),)), "x", 15.3)
    delta = 15.3 - 12
    assert out.elements[1] == Line(Point(5 + delta, 1), Point(10 + delta, 1))


def test_the_weight_defaults_to_one_and_is_written_only_when_it_is_not():
    assert Stretch("x", 1).weight == 1
    written = symbol_to_data(base())["stretch"]
    assert written == [{"axis": "x", "at": 4}, {"axis": "x", "at": 8, "weight": 3}]
    assert round_trips(base())


TOML = """schema = 1
name = "w"
kind = "element"
status = "unverified"
reference = { standard = "X", number = "1" }
stretch = [{ axis = "x", at = 1, weight = WEIGHT }]
elements = [{ line = [[0, 0], [4, 0]] }]
"""


@pytest.mark.parametrize("weight", ["0", "-1", "0.0"])
def test_a_weight_that_is_not_positive_is_a_schema_finding(weight):
    data, _ = parse_toml(TOML.replace("WEIGHT", weight))
    assert [f.location for f in validate(data)] == ["/stretch/0/weight"]


def test_a_weight_loads():
    data, _ = parse_toml(TOML.replace("WEIGHT", "2.5"))
    assert data is not None
    assert validate(data) == ()
    assert symbol_from_data(data).stretch == (Stretch("x", 1, 2.5),)


def test_a_weight_that_is_not_a_number_is_a_schema_finding():
    data, _ = parse_toml(TOML.replace("WEIGHT", '"a"'))
    assert [f.location for f in validate(data)] == ["/stretch/0/weight"]


# D69: slots follow the cuts.


def test_a_slot_box_across_a_cut_grows_by_the_cuts_share():
    slot = Slot("s", Point(2, 0), E, (4, 2))  # x 2..6 across the cut at 4
    out = stretch(base(slots=(slot,), cuts=(Stretch("x", 4),)), "x", 20).slots[0]
    assert slot_box(out).min.x == 2
    assert slot_box(out).max.x == 6 + 8
    assert out.box == (12, 2)


def test_a_slot_box_across_two_weighted_cuts_grows_by_both_shares():
    slot = Slot("s", Point(2, 0), E, (8, 2))  # x 2..10 across both cuts
    out = stretch(base(slots=(slot,)), "x", 20).slots[0]
    assert out.box == (16, 2)
    assert slot_box(out).max.x == 18


@pytest.mark.parametrize("side", [N, S])
def test_a_side_slot_across_a_cut_keeps_its_ss17_position_and_grows_its_box(side):
    out = stretch(base(slots=(Slot("s", Point(4, 3), side, (4, 2)),)), "x", 20).slots[0]
    assert out.position.x == 4  # not beyond the cut at 4, so it does not move
    assert out.box == (4 + 2, 2)


@pytest.mark.parametrize("side", [N, S])
def test_a_side_slot_beyond_a_cut_moves_by_its_share_and_its_box_grows(side):
    slot = Slot("s", Point(5, 3), side, (4, 2))  # box x 3..7 spans the cut at 4; 5 lies beyond it
    out = stretch(base(slots=(slot,), cuts=(Stretch("x", 4),)), "x", 20).slots[0]  # grown by 8
    assert out.position.x == 5 + 8  # the position lies beyond the cut: it moves by the share
    assert out.box == (4 + 8, 2)  # the box spans the cut: it grows by the share


@pytest.mark.parametrize("side", [W, E])
def test_a_w_or_e_slot_across_a_y_cut_moves_by_the_cut_shares_not_to_the_box_centre(side):
    tall = base(
        slots=(Slot("s", Point(0, 6), side, (3, 4)), Slot("c", Point(1, 6), Centre.C, (3, 4))),
        cuts=(Stretch("y", 5),),  # both boxes span y 4..8 across the cut; positions lie beyond it
    )
    tall = replace(tall, elements=(Line(Point(0, 0), Point(0, 12)),))
    s, c = stretch(tall, "y", 20).slots  # grown by 8
    assert s.position.y == 6 + 8  # the cut share, as in 0.9.0
    assert s.box == (3, 4 + 8)
    assert c.position.y == 6 + 4  # a C slot sits at its stretched box centre
    assert c.box == (3, 4 + 8)


def test_a_turned_slot_grows_along_its_authored_box():
    slot = Slot("s", Point(2, 0), W, (2, 6), turn=True)  # W: x 0..2; y -3..3
    out = stretch(base(slots=(slot,)), "x", 20).slots[0]
    assert out.turn
    assert out.box == (2, 6)


def test_a_slot_wholly_beyond_a_cut_moves_and_keeps_its_box():
    slot = Slot("s", Point(9, 0), E, (3, 1))
    out = stretch(base(slots=(slot,)), "x", 20).slots[0]
    assert out.position == Point(17, 0)
    assert out.box == (3, 1)


def test_a_slot_grows_along_the_y_axis_the_same_way():
    tall = base(
        Line(Point(0, 0), Point(0, 12)),
        slots=(Slot("s", Point(0, 2), S, (1, 6)),),  # y 2..8 across the cut at 4
        cuts=(Stretch("y", 4),),
    )
    out = stretch(replace(tall, elements=tall.elements[1:]), "y", 20).slots[0]
    assert out.box == (1, 14)
    assert out.position == Point(0, 2)


COORD = st.integers(0, 40).map(float)


@given(
    cuts=st.lists(
        st.tuples(COORD, st.integers(1, 9)), min_size=1, max_size=3, unique_by=lambda c: c[0]
    ),
    side=st.sampled_from([E, W, Centre.C]),  # N and S are centred on x: see the test above
    at=COORD,
    size=st.tuples(st.integers(1, 20), st.integers(1, 20)).map(
        lambda t: (float(t[0]), float(t[1]))
    ),
    grow=st.integers(0, 30).map(float),
)
def test_the_stretched_slot_box_is_the_old_box_with_each_corner_moved(cuts, side, at, size, grow):
    stretches = tuple(Stretch("x", c, w) for c, w in cuts)
    slot = Slot("s", Point(at, 5), side, size)
    symbol = base(slots=(slot,), cuts=stretches)
    symbol = replace(symbol, elements=(Line(Point(0, 0), Point(60, 0)),))
    total = sum(w for _, w in cuts)

    def shift(x: float) -> float:
        if len(cuts) == 1:
            return grow if x > cuts[0][0] else 0.0
        return sum(grow * w / total for c, w in cuts if x > c)

    old = slot_box(slot)
    new = slot_box(stretch(symbol, "x", 60 + grow).slots[0])
    assert new.min.x == pytest.approx(old.min.x + shift(old.min.x))
    assert new.max.x == pytest.approx(old.max.x + shift(old.max.x))
    assert (new.min.y, new.max.y) == (old.min.y, old.max.y)
