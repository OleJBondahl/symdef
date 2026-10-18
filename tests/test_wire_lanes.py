"""`wire(..., lanes=, pitch=)`: parallel lanes, lane 0 on the points (D99)."""

from dataclasses import replace

import pytest
from test_wire import LIBRARY, PATH, polyline_of

from symdef.errors import InvalidValueError
from symdef.geometry import Polyline
from symdef.units import Grid
from symdef.wire import wire


def lanes_of(symbol) -> list[tuple[tuple[float, float], ...]]:
    return [tuple((p.x, p.y) for p in e.points) for e in symbol.elements]


def test_one_lane_is_the_wire_of_before():
    assert wire(LIBRARY, "link", PATH, lanes=1) == wire(LIBRARY, "link", PATH)
    assert wire(LIBRARY, "link", PATH, lanes=1, pitch=3) == wire(LIBRARY, "link", PATH)
    assert len(wire(LIBRARY, "link", PATH).elements) == 1


def test_three_lanes_of_a_horizontal_run_step_towards_plus_y():
    symbol = wire(LIBRARY, "trunk", [(0, 0), (10, 0)], lanes=3)
    assert lanes_of(symbol) == [((0, 0), (10, 0)), ((0, 1), (10, 1)), ((0, 2), (10, 2))]
    one = polyline_of(wire(LIBRARY, "trunk", PATH))
    for lane in symbol.elements:
        assert isinstance(lane, Polyline)
        assert (lane.weight, lane.style) == (one.weight, one.style)


def test_lanes_of_a_vertical_run_step_towards_plus_x_whichever_way_it_runs():
    down = wire(LIBRARY, "wire", [(0, 0), (0, 10)], lanes=2)
    up = wire(LIBRARY, "wire", [(0, 10), (0, 0)], lanes=2)
    assert lanes_of(down) == [((0, 0), (0, 10)), ((1, 0), (1, 10))]
    assert lanes_of(up) == [((0, 10), (0, 0)), ((1, 10), (1, 0))]


def test_a_horizontal_run_going_left_still_steps_towards_plus_y():
    assert lanes_of(wire(LIBRARY, "wire", [(10, 0), (0, 0)], lanes=2))[1] == ((10, 1), (0, 1))


def test_a_corner_is_mitred_and_the_outer_lane_runs_longer():
    symbol = wire(LIBRARY, "wire", [(0, 0), (10, 0), (10, 10)], lanes=2)
    assert lanes_of(symbol) == [
        ((0, 0), (10, 0), (10, 10)),
        ((0, 1), (11, 1), (11, 10)),
    ]


def test_a_turn_from_vertical_to_horizontal_is_mitred_by_the_same_side_rule():
    symbol = wire(LIBRARY, "wire", [(0, 0), (0, 10), (10, 10)], lanes=2)
    assert lanes_of(symbol)[1] == ((1, 0), (1, 11), (10, 11))


def test_a_straight_join_of_two_runs_moves_with_them():
    symbol = wire(LIBRARY, "wire", [(0, 0), (4, 0), (10, 0)], lanes=2)
    assert lanes_of(symbol)[1] == ((0, 1), (4, 1), (10, 1))


def test_an_explicit_pitch_sets_the_spacing():
    symbol = wire(LIBRARY, "wire", [(0, 0), (10, 0)], lanes=3, pitch=2.0)
    assert [lane[0][1] for lane in lanes_of(symbol)] == [0, 2, 4]


def test_the_default_pitch_is_the_grids_wire_pitch_in_modules():
    grid = Grid(divisions_per_module=8, wire_pitch=16, wire_pitch_fine=8)
    library = replace(LIBRARY, grid=grid)
    symbol = wire(library, "wire", [(0, 0), (10, 0)], lanes=2)
    assert lanes_of(symbol)[1] == ((0, 2), (10, 2))
    assert lanes_of(wire(LIBRARY, "wire", [(0, 0), (10, 0)], lanes=2))[1][0] == (0, 1)


@pytest.mark.parametrize(
    ("kwargs", "words"),
    [
        ({"lanes": 0}, "lanes must be at least 1, got 0"),
        ({"lanes": -2}, "got -2"),
        ({"lanes": 2, "closed": True}, "closed wire has one lane, got lanes=2"),
        ({"lanes": 2, "pitch": 0}, "pitch must be above 0, got 0"),
        ({"lanes": 2, "pitch": -1.5}, "got -1.5"),
        ({"pitch": 0}, "pitch must be above 0"),
    ],
)
def test_a_bad_lane_value_raises_naming_the_value_and_the_fix(kwargs, words):
    with pytest.raises(InvalidValueError, match=words) as error:
        wire(LIBRARY, "wire", PATH, **kwargs)
    assert ";" in str(error.value)


def test_a_closed_wire_with_one_lane_is_allowed():
    assert polyline_of(wire(LIBRARY, "wire", PATH, closed=True, lanes=1)).closed is True


def test_a_slanted_or_empty_run_cannot_take_lanes():
    for points in ([(0, 0), (3, 4)], [(0, 0), (0, 0)]):
        with pytest.raises(InvalidValueError, match="horizontal or vertical"):
            wire(LIBRARY, "wire", points, lanes=2)
