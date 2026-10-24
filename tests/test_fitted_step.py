"""`fitted_table(fit="step")`: rows grow along the stepping axis to their widest text."""

import itertools
from dataclasses import replace

import pytest
from test_fitted import HEIGHT, LIB, MID, SHORT, WIDE, build, up
from test_font import FONT

from symdef.boxes import body_box, slot_box
from symdef.errors import InvalidValueError
from symdef.fitted import fitted_table
from symdef.geometry import Direction, Line, Point
from symdef.model import Slot, Stretch
from symdef.orient import Orientation, orient
from symdef.repeat import MAX_REPEAT
from symdef.slottext import text_box
from symdef.table import table

GRID = LIB.grid
# Rows step along x; the marking text runs along x too. The cut on x lies inside the slot's box,
# the cut on y is shared with the head.
ROW = build(
    Line(Point(0, 0), Point(10, 0)),
    Line(Point(0, 2), Point(10, 2)),
    slots=(Slot("marking.a", Point(1, 1), Direction.E, (4, 1)),),
    cuts=(Stretch("x", 3), Stretch("y", 1)),
)
# A head left of the rows: same y frame, its own cut on x across its slot.
HEAD = build(
    Line(Point(-8, 0), Point(0, 0)),
    Line(Point(-8, 2), Point(0, 2)),
    slots=(Slot("h", Point(-7, 1), Direction.E, (4, 1)),),
    cuts=(Stretch("x", -5), Stretch("y", 1)),
)
# Rows step along y; the marking text is turned and runs along y.
COLUMN = build(
    Line(Point(0, 0), Point(0, 10)),
    Line(Point(2, 0), Point(2, 10)),
    slots=(Slot("marking.a", Point(1, 1), Direction.S, (1, 4), turn=True),),
    cuts=(Stretch("y", 3),),
)


def texts(*values):
    return [{"marking.a": v} for v in values]


def step_of(t, n, axis="x"):
    box = body_box(t)
    return (box.width if axis == "x" else box.height) / n


def marking_boxes(t, values):
    """Each row's marking text box, measured in place."""
    slots = {s.id: s for s in t.slots}
    return [
        text_box(slots[f"marking.{k}.a"], v, HEIGHT, FONT, GRID)
        for k, v in enumerate(values, start=1)
    ]


def check_clear(boxes, axis):
    lows = [b.min.x if axis == "x" else b.min.y for b in boxes]
    highs = [b.max.x if axis == "x" else b.max.y for b in boxes]
    assert all(h <= low + 1e-9 for h, low in zip(highs, lows[1:], strict=False))


@pytest.mark.parametrize("n", [1, 2, 3, MAX_REPEAT])
def test_every_row_takes_the_widest_text_and_boxes_stay_clear(n):
    values = [MID if k == 0 else SHORT for k in range(n)]
    t = fitted_table(ROW, "x", texts(*values), LIB, HEIGHT, fit="step", port_format="{k}.{port}")
    assert step_of(t, n) == 10 + up(MID) - 4
    for k in range(1, n + 1):
        box = slot_box(next(s for s in t.slots if s.id == f"marking.{k}.a"))
        assert box.width == up(MID)
    assert t.stretch == ()
    check_clear(marking_boxes(t, values), "x")


def test_a_long_text_and_a_short_text_give_different_steps():
    long = fitted_table(
        ROW, "x", texts(WIDE, SHORT), LIB, HEIGHT, fit="step", port_format="{k}.{port}"
    )
    short = fitted_table(
        ROW, "x", texts(MID, SHORT), LIB, HEIGHT, fit="step", port_format="{k}.{port}"
    )
    assert step_of(long, 2) - step_of(short, 2) == up(WIDE) - up(MID)
    assert step_of(long, 2) > step_of(short, 2) > 6


def test_the_y_axis_steps_a_turned_column():
    t = fitted_table(
        COLUMN, "y", texts(MID, SHORT), LIB, HEIGHT, fit="step", port_format="{k}.{port}"
    )
    assert step_of(t, 2, "y") == 10 + up(MID) - 4
    assert body_box(t).width == 2
    check_clear(marking_boxes(t, [MID, SHORT]), "y")


def test_a_text_that_fits_asks_for_no_growth():
    t = fitted_table(ROW, "x", texts("A", "A"), LIB, HEIGHT, fit="step", port_format="{k}.{port}")
    plain = table(ROW, 2, "x", grid=GRID, port_format="{k}.{port}")
    assert t.elements == plain.elements
    assert t.slots == plain.slots


def test_cross_is_the_default_and_unchanged():
    args = (ROW, "y", [{"marking.a": MID}] * 2, LIB, HEIGHT)
    assert fitted_table(*args, port_format="{k}.{port}") == fitted_table(
        *args, fit="cross", port_format="{k}.{port}"
    )
    assert body_box(fitted_table(*args, port_format="{k}.{port}")).width == 10 + up(MID) - 4


def test_a_row_without_the_cut_on_the_axis_cannot_step_grow():
    bare = build(*ROW.elements, slots=ROW.slots, cuts=(Stretch("y", 1),))
    with pytest.raises(InvalidValueError, match="no stretch cut across its box on the x axis"):
        fitted_table(bare, "x", texts(MID), LIB, HEIGHT, fit="step", port_format="{k}.{port}")


def test_fit_is_cross_or_step():
    with pytest.raises(InvalidValueError, match="fit must be 'cross' or 'step', got 'both'"):
        fitted_table(ROW, "x", texts(MID), LIB, HEIGHT, fit="both", port_format="{k}.{port}")  # ty: ignore[invalid-argument-type]  # a bad value on purpose


def head_part(t, n_head_elements):
    return body_box(replace(t, elements=t.elements[:n_head_elements]))


def test_head_texts_grow_the_head_along_the_axis_and_it_is_not_stretched():
    short = fitted_table(
        ROW, "x", texts(SHORT, SHORT), LIB, HEIGHT, fit="step", head=HEAD, port_format="{k}.{port}"
    )
    long = fitted_table(
        ROW,
        "x",
        texts(SHORT, SHORT),
        LIB,
        HEIGHT,
        fit="step",
        head=HEAD,
        head_texts={"h": WIDE},
        port_format="{k}.{port}",
    )
    assert head_part(short, 2).width == 20  # stretched to span the two rows
    assert head_part(long, 2).width == 4 + up(WIDE)  # grown at its own cut, not stretched
    assert width_of(long, "h") == up(WIDE)


def width_of(t, slot_id):
    return slot_box(next(s for s in t.slots if s.id == slot_id)).width


def test_a_head_of_three_lines_is_taller_than_one_of_one_line_and_the_rows_agree():
    def build_with(text):
        return fitted_table(
            ROW,
            "x",
            texts(SHORT, SHORT),
            LIB,
            HEIGHT,
            fit="step",
            head=HEAD,
            head_texts={"h": text},
            port_format="{k}.{port}",
        )

    one, three = build_with("AB"), build_with("AB\nAB\nAB")
    assert head_part(three, 2).height > head_part(one, 2).height
    assert body_box(three).height == head_part(three, 2).height
    assert body_box(one).height == head_part(one, 2).height


def test_a_head_text_that_fits_leaves_the_head_to_be_stretched():
    t = fitted_table(
        ROW,
        "x",
        texts(SHORT, SHORT),
        LIB,
        HEIGHT,
        fit="step",
        head=HEAD,
        head_texts={"h": "A"},
        port_format="{k}.{port}",
    )
    assert head_part(t, 2).width == 20


def test_the_head_needs_a_cut_across_its_slot_on_the_axis():
    bare = replace(HEAD, stretch=(Stretch("y", 1),))
    with pytest.raises(InvalidValueError, match="no stretch cut across its box on the x axis"):
        fitted_table(
            ROW,
            "x",
            texts(SHORT),
            LIB,
            HEIGHT,
            fit="step",
            head=bare,
            head_texts={"h": WIDE},
            port_format="{k}.{port}",
        )


def test_a_table_fitted_unturned_then_turned_keeps_its_step_on_the_turned_axis():
    """Fit along the step axis in the unturned frame, then orient the result (R270)."""
    values = [WIDE, SHORT, MID]
    fitted = fitted_table(
        ROW, "x", texts(*values), LIB, HEIGHT, fit="step", port_format="{k}.{port}"
    )
    step = step_of(fitted, 3)
    check_clear(marking_boxes(fitted, values), "x")
    turned = orient(fitted, Orientation.R270)
    ys = sorted({s.position.y for s in turned.slots})
    xs = sorted({s.position.x for s in turned.slots})
    assert len(ys) == 3
    assert len(xs) == 1
    assert [round(b - a, 9) for a, b in itertools.pairwise(ys)] == [step, step]
