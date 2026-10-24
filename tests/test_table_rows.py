"""`table`: unlike rows, gaps, positions and head alignment, ports numbered per row."""

import pytest
from test_table import head, row

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.geometry import Line, Point, Style, Weight
from symdef.model import Stretch
from symdef.repeat import MAX_REPEAT
from symdef.table import table


def line(x0, y0, x1, y1):
    return Line(Point(x0, y0), Point(x1, y1), Weight.NORMAL, Style.SOLID)


def tall():
    """A row four high (y -2 to 2) and four wide, with the same ports as `row()`."""
    return row(elements=(line(0, -2, 4, -2), line(0, 2, 4, 2)))


def ports(t):
    return {p.id: p.position for p in t.ports}


def test_a_sequence_of_equal_rows_is_the_same_table():
    r = row()
    for axis in ("x", "y"):
        assert table([r, r, r], 3, axis, port_format="{k}.{port}") == table(
            r, 3, axis, port_format="{k}.{port}"
        )
        assert table((r,) * 3, 3, axis, gaps=[0, 0], port_format="{k}.{port}") == table(
            r, 3, axis, port_format="{k}.{port}"
        )


@pytest.mark.parametrize("axis", ["x", "y"])
@pytest.mark.parametrize("n", [1, 3, MAX_REPEAT])
def test_ports_are_numbered_per_row_and_stepped_by_the_extent(axis, n):
    r = row()
    t = table(r, n, axis, port_format="{k}.{port}")
    assert [p.id for p in t.ports] == [f"{k}.{i}" for k in range(1, n + 1) for i in ("in", "out")]
    step = body_box(r).width if axis == "x" else body_box(r).height
    for k in range(1, n + 1):
        at = ports(t)[f"{k}.in"]
        assert (at.x, at.y) == ((-2 + (k - 1) * step, 0) if axis == "x" else (-2, (k - 1) * step))
    assert [p.id for p in table([r] * n, n, axis, port_format="{k}.{port}").ports] == [
        p.id for p in t.ports
    ]


def test_unlike_rows_advance_by_their_own_extent():
    t = table([row(), tall(), row()], 3, "y", port_format="{k}.{port}")
    assert [ports(t)[f"{k}.in"].y for k in (1, 2, 3)] == [0, 3, 6]
    assert [p.id for p in t.ports][:4] == ["1.in", "1.out", "2.in", "2.out"]
    assert t.name == "row"
    assert [s.id for s in t.slots][:2] == ["marking.1.in", "1.x"]


def test_unlike_rows_on_x_keep_each_rows_own_ports():
    t = table([tall(), row()], 2, "x", port_format="{k}.{port}")
    assert [ports(t)[f"{k}.out"].x for k in (1, 2)] == [4, 10]


def test_the_row_count_must_match_the_sequence_and_stay_bounded():
    with pytest.raises(InvalidValueError, match="table got 2 rows but n is 3; pass n equal to"):
        table([row(), row()], 3, "y", port_format="{k}.{port}")
    with pytest.raises(InvalidValueError, match="between 1 and 64, got 65"):
        table([row()] * 65, 65, "y", port_format="{k}.{port}")
    with pytest.raises(InvalidValueError, match="between 1 and 64, got 0"):
        table([], 0, "y", port_format="{k}.{port}")


def test_gaps_add_space_after_each_row_but_the_last():
    t = table(row(), 3, "y", gaps=[1, 2], port_format="{k}.{port}")
    assert [ports(t)[f"{k}.in"].y for k in (1, 2, 3)] == [0, 3, 7]


def test_gaps_are_checked():
    with pytest.raises(InvalidValueError, match="gaps needs 2 numbers, one after each row but"):
        table(row(), 3, "y", gaps=[1], port_format="{k}.{port}")
    with pytest.raises(InvalidValueError, match="the gap after row 2 is -1; use 0 or more"):
        table(row(), 3, "y", gaps=[0, -1], port_format="{k}.{port}")


def test_positions_place_each_rows_low_edge():
    t = table(row(), 3, "y", positions=[10, 20, 22], port_format="{k}.{port}")
    assert [ports(t)[f"{k}.in"].y for k in (1, 2, 3)] == [11, 21, 23]
    assert body_box(t).min.y == 10


def test_positions_are_checked():
    with pytest.raises(
        InvalidValueError, match="positions needs 3 numbers, one for each row, got 2"
    ):
        table(row(), 3, "y", positions=[0, 5], port_format="{k}.{port}")
    with pytest.raises(InvalidValueError, match="row 3 starts at 3, inside row 2, which ends at 4"):
        table(row(), 3, "y", positions=[0, 2, 3], port_format="{k}.{port}")
    with pytest.raises(InvalidValueError, match="gaps and positions are mutually exclusive"):
        table(row(), 2, "y", gaps=[0], positions=[0, 2], port_format="{k}.{port}")


def wide_head(**fields):
    """A head 20 wide along x with port `h` at its authored (0, 0)."""
    return head(line(0, 0, 20, 0), **fields)


def test_a_head_wider_than_the_rows_moves_the_rows():
    # two rows, each 6 wide from x = -2, so the rows span -2 to 10
    expected = {"start": 0, "center": 4, "end": 8}
    for align, low in expected.items():
        t = table(row(), 2, "x", wide_head(), head_align=align, port_format="{k}.{port}")  # ty: ignore[invalid-argument-type]  # a bad value on purpose
        assert ports(t)["1.in"].x == low
        assert ports(t)["2.in"].x == low + 6
        assert ports(t)["h"].x == 0


def test_a_head_narrower_than_the_rows_moves():
    for align, shift in {"start": -2, "center": 2, "end": 6}.items():
        t = table(row(), 2, "x", head(line(0, 0, 4, 0)), head_align=align, port_format="{k}.{port}")
        assert ports(t)["h"].x == shift
        assert ports(t)["1.in"].x == -2


def test_an_equal_head_lines_up_and_aligned_with_nothing_to_move_is_as_authored():
    h = head(line(-2, 0, 10, 0))
    plain = table(row(), 2, "x", h, port_format="{k}.{port}")
    for align in ("start", "center", "end"):
        assert table(row(), 2, "x", h, head_align=align, port_format="{k}.{port}") == plain
    moved = table(
        row(), 2, "x", head(line(0, 0, 12, 0)), head_align="end", port_format="{k}.{port}"
    )
    assert ports(moved)["h"].x == -2


def test_a_head_with_a_cut_spans_the_rows_then_lines_up():
    h = head(line(0, 0, 2, 0), stretch=(Stretch("x", 1),))
    t = table(row(), 2, "x", h, head_align="center", port_format="{k}.{port}")
    assert body_box(t).width == 12
    assert ports(t)["h"].x == -2


def test_a_wider_head_with_a_cut_is_not_stretched_when_aligned():
    h = wide_head(stretch=(Stretch("x", 4),))
    t = table(row(), 2, "x", h, head_align="start", port_format="{k}.{port}")
    assert ports(t)["1.in"].x == 0
    assert body_box(t).width == 20
    with pytest.raises(InvalidValueError, match="below the natural extent"):
        table(row(), 2, "x", h, port_format="{k}.{port}")


def test_head_align_is_one_of_three_even_without_a_head():
    msg = "head_align must be one of 'start', 'center' or 'end', got 'middle'"
    with pytest.raises(InvalidValueError, match=msg):
        table(row(), 2, "x", wide_head(), head_align="middle", port_format="{k}.{port}")  # ty: ignore[invalid-argument-type]  # a bad value on purpose
    with pytest.raises(InvalidValueError, match=msg):
        table(row(), 2, "x", head_align="middle", port_format="{k}.{port}")  # ty: ignore[invalid-argument-type]  # a bad value on purpose


def test_head_align_without_a_head_changes_nothing():
    assert table(row(), 2, "x", head_align="end", port_format="{k}.{port}") == table(
        row(), 2, "x", port_format="{k}.{port}"
    )
