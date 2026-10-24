"""`fitted_table`: each column is as wide as its widest text, rounded up to the grid (D94)."""

import math
from dataclasses import replace

import pytest
from test_font import FONT

from symdef.boxes import body_box, keepout_box, slot_box
from symdef.errors import InvalidValueError, UnknownNameError
from symdef.fitted import fitted_table
from symdef.font import text_width
from symdef.geometry import Direction, Line, Point
from symdef.gridmeasure import measure
from symdef.model import Library, Reference, Slot, Status, Stretch, Symbol, SymbolKind
from symdef.orient import Orientation
from symdef.table import table
from symdef.units import Grid

HEIGHT = 2
LIB = Library("S", "S", "", {}, font=FONT, grid=Grid(divisions_per_module=8))
SHORT, MID, WIDE = "AB", "ABiAB", "ABiABAB"


def up(text):
    """The text's width at HEIGHT in modules, rounded up to eighths, worked apart from symdef."""
    return math.ceil(round(text_width(FONT, text, HEIGHT) * 8, 6)) / 8


def build(*elements, slots=(), cuts=()):
    return Symbol(
        "row",
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", "1"),
        elements,
        slots=slots,
        stretch=cuts,
    )


# Rows stack in y; two columns across x. The slot boxes are 4 and 3 wide, the cuts inside them.
ROW = build(
    Line(Point(0, 0), Point(10, 0)),
    Line(Point(0, 2), Point(10, 2)),
    slots=(
        Slot("a", Point(1, 1), Direction.E, (4, 1)),
        Slot("b", Point(6, 1), Direction.E, (3, 1)),
    ),
    cuts=(Stretch("x", 3), Stretch("x", 7.5)),
)
HEAD = build(
    Line(Point(0, -2), Point(10, -2)),
    Line(Point(0, 0), Point(10, 0)),
    slots=(Slot("h", Point(1, -1), Direction.E, (4, 1)),),
    cuts=(Stretch("x", 3),),
)


def width(symbol, slot_id):
    box = slot_box(next(s for s in symbol.slots if s.id == slot_id))
    return box.width


def test_column_is_widest_text_rounded_up_and_the_other_keeps_its_box():
    result = fitted_table(
        ROW, "y", [{"a": SHORT, "b": "A"}, {"a": MID}], LIB, HEIGHT, port_format="{k}.{port}"
    )
    assert width(result, "1.a") == width(result, "2.a") == up(MID)
    assert up(MID) > 4
    assert width(result, "1.b") == width(result, "2.b") == 3
    assert body_box(result).width == 10 + up(MID) - 4
    assert result.stretch == ()


def test_a_planted_wider_text_widens_its_column_by_its_width_rounded_up():
    before = fitted_table(
        ROW, "y", [{"a": MID}, {"a": SHORT}], LIB, HEIGHT, port_format="{k}.{port}"
    )
    after = fitted_table(ROW, "y", [{"a": MID}, {"a": WIDE}], LIB, HEIGHT, port_format="{k}.{port}")
    assert up(WIDE) != text_width(FONT, WIDE, HEIGHT)
    assert width(after, "1.a") == up(WIDE)
    assert width(before, "1.a") == up(MID)
    assert width(after, "1.a") - width(before, "1.a") == up(WIDE) - up(MID)
    assert body_box(after).width - body_box(before).width == up(WIDE) - up(MID)


def test_a_head_text_counts_in_its_column():
    plain = fitted_table(ROW, "y", [{"a": SHORT}], LIB, HEIGHT, head=HEAD, port_format="{k}.{port}")
    headed = fitted_table(
        ROW,
        "y",
        [{"a": SHORT}],
        LIB,
        HEIGHT,
        head=HEAD,
        head_texts={"h": WIDE},
        port_format="{k}.{port}",
    )
    assert width(plain, "1.a") == 4
    assert width(headed, "1.a") == width(headed, "h") == up(WIDE)
    assert body_box(headed).width == 10 + up(WIDE) - 4


def test_the_result_is_an_ordinary_symbol_for_measure_and_the_boxes():
    result = fitted_table(ROW, "y", [{"a": MID}] * 3, LIB, HEIGHT, port_format="{k}.{port}")
    view = measure(result, Orientation.R0, LIB)
    assert view.body.max.x == math.ceil(body_box(result).width * 8)
    assert view.slots["3.a"].max.x - view.slots["3.a"].min.x == up(MID) * 8
    assert keepout_box(result).width >= body_box(result).width
    assert body_box(result).height == body_box(table(ROW, 3, "y", port_format="{k}.{port}")).height


def test_no_growth_when_every_text_fits_gives_the_plain_table():
    result = fitted_table(ROW, "y", [{"a": "A"}, {"b": "A"}], LIB, HEIGHT, port_format="{k}.{port}")
    assert result == table(replace(ROW, stretch=()), 2, "y", port_format="{k}.{port}")


def test_the_x_axis_grows_the_columns_along_y():
    column = build(
        Line(Point(0, 0), Point(0, 10)),
        Line(Point(2, 0), Point(2, 10)),
        slots=(Slot("a", Point(1, 1), Direction.S, (1, 4), turn=True),),
        cuts=(Stretch("y", 3),),
    )
    result = fitted_table(
        column, "x", [{"a": MID}, {"a": SHORT}], LIB, HEIGHT, port_format="{k}.{port}"
    )
    assert slot_box(next(s for s in result.slots if s.id == "1.a")).height == up(MID)
    assert body_box(result).height == 10 + up(MID) - 4
    assert body_box(result).width == 4


def test_errors_name_the_thing_and_the_fix():
    with pytest.raises(InvalidValueError, match="font"):
        fitted_table(
            ROW, "y", [{"a": MID}], replace(LIB, font=None), HEIGHT, port_format="{k}.{port}"
        )
    with pytest.raises(InvalidValueError, match="text height"):
        fitted_table(ROW, "y", [{"a": MID}], LIB, 0, port_format="{k}.{port}")
    with pytest.raises(UnknownNameError, match="no such slot: z"):
        fitted_table(ROW, "y", [{"z": MID}], LIB, HEIGHT, port_format="{k}.{port}")
    with pytest.raises(InvalidValueError, match="no stretch cut across its box"):
        fitted_table(
            replace(ROW, stretch=()), "y", [{"a": MID}], LIB, HEIGHT, port_format="{k}.{port}"
        )
    with pytest.raises(InvalidValueError, match="head_texts needs a head"):
        fitted_table(
            ROW, "y", [{"a": MID}], LIB, HEIGHT, head_texts={"h": MID}, port_format="{k}.{port}"
        )
    with pytest.raises(InvalidValueError, match="no stretch cut on the x axis at 3"):
        fitted_table(
            ROW,
            "y",
            [{"a": MID}],
            LIB,
            HEIGHT,
            head=replace(HEAD, stretch=(Stretch("x", 4),)),
            port_format="{k}.{port}",
        )
    with pytest.raises(InvalidValueError, match="row count"):
        fitted_table(ROW, "y", [], LIB, HEIGHT, port_format="{k}.{port}")


def test_fitted_table_reads_the_given_port_format():
    texts = [{"a": SHORT}, {"a": MID}]
    result = fitted_table(ROW, "y", texts, LIB, HEIGHT, port_format="P{k}_{port}")
    assert [s.id for s in result.slots] == ["P1_a", "P1_b", "P2_a", "P2_b"]
