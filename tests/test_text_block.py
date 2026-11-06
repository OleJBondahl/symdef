"""`[font] text_block`: "grid" sets a block as render does, "cap" keeps symdef's (D95)."""

import math
from dataclasses import replace

import pytest
from test_font import BOLD

from symdef import Centre, Point, Slot, Weight, slot_lines, slot_text
from symdef.boxes import slot_box
from symdef.font import FontMetrics, text_footprint, text_width
from symdef.load import font_from_data
from symdef.model import Library
from symdef.serialize import bundle_to_data
from symdef.slottext import text_box
from symdef.units import DEFAULT_GRID, Grid

MODULE_MM = 1.875
GRID = Grid(module_mm=MODULE_MM, divisions_per_module=8)
G_MM = MODULE_MM / 8
UPM, CAP, ASCENT = 2048, 1493, 1556
FONT_MM = 1.8 * UPM / CAP  # render: a 1.8 mm capital gives this font size
HEIGHT = FONT_MM / MODULE_MM  # the same size in modules
GRID_FONT = FontMetrics(
    "Planted",
    UPM,
    CAP,
    ASCENT,
    400,
    {Weight.NORMAL: BOLD, Weight.THICK: BOLD},
    {Weight.NORMAL: 600, Weight.THICK: 600},
    text_block="grid",
)
CAP_FONT = replace(GRID_FONT, text_block="cap")
BOX_G = 12


def render_baselines_mm(count):
    """Render's baselines in a 67x12 G box at y = 0 (`_markers._text_element`), from its formula."""
    room = math.ceil(FONT_MM / G_MM)
    pad = (BOX_G - count * room) // 2
    return [(pad + i * room) * G_MM + FONT_MM * ASCENT / UPM for i in range(count)]


def star_slot():
    """A centred slot at the middle of the 12 G box."""
    return Slot("c", Point(67 / 16, BOX_G / 16), Centre.C, (4, 1))


@pytest.mark.parametrize("count", [1, 3])
def test_a_grid_block_sits_where_render_puts_it_in_a_67_by_12_g_star(count):
    text = "\n".join("AB" for _ in range(count))
    got = [p.point.y * MODULE_MM for p in slot_lines(star_slot(), text, HEIGHT, GRID_FONT, GRID)]
    assert got == pytest.approx(render_baselines_mm(count), abs=1e-6)


def test_a_grid_block_box_is_whole_rows_so_three_lines_fill_33_g():
    box = text_box(star_slot(), "A\nB\nC", HEIGHT, GRID_FONT, GRID)
    assert box.height * MODULE_MM == pytest.approx(33 * G_MM, abs=1e-6)
    assert slot_box(star_slot(), "A\nB\nC", HEIGHT, GRID_FONT, GRID).height * 8 >= 33


def test_slot_text_in_grid_is_the_one_line_block():
    one = slot_text(star_slot(), "AB", HEIGHT, GRID_FONT, GRID)
    assert one.point.y * MODULE_MM == pytest.approx(render_baselines_mm(1)[0], abs=1e-6)


def test_the_cap_rule_keeps_the_cap_pitch_and_centre():
    cap = CAP / UPM * HEIGHT
    first, second = slot_lines(star_slot(), "AB\nCD", HEIGHT, CAP_FONT, GRID)
    y = BOX_G / 16
    assert first.point.y == pytest.approx(y + 0.5 * cap - 0.75 * cap)
    assert second.point.y == pytest.approx(y + 0.5 * cap + 0.75 * cap)


def test_the_bundle_carries_a_grid_rule_and_leaves_the_cap_default_out():
    grid = bundle_to_data(Library("S", "S", "", {}, font=GRID_FONT, port_format="{k}.{port}"))[
        "font"
    ]
    assert grid["text_block"] == "grid"
    assert font_from_data(grid).text_block == "grid"
    assert (
        "text_block"
        not in bundle_to_data(Library("S", "S", "", {}, font=CAP_FONT, port_format="{k}.{port}"))[
            "font"
        ]
    )


def test_footprint_of_one_line_is_its_width_by_one_em_box_under_either_rule():
    em_divisions = math.ceil(HEIGHT * 8 - 1e-9)
    for font in (CAP_FONT, GRID_FONT):
        width, height = text_footprint(font, "K1", 1.8, GRID)
        assert height == em_divisions
        assert width == math.ceil(text_width(font, "K1", HEIGHT) * 8 - 1e-9)
    assert text_footprint(None, "K1", 1.6, DEFAULT_GRID) == (9, 8)


def test_footprint_of_two_lines_is_the_widest_line_by_the_block_height():
    one_w, one_h = text_footprint(CAP_FONT, "K1", 1.8, GRID)
    wide_w, _ = text_footprint(CAP_FONT, "K1234", 1.8, GRID)
    cap_w, cap_h = text_footprint(CAP_FONT, "K1234\nK1", 1.8, GRID)
    assert cap_w == wide_w  # the widest line, not the sum
    # an em box plus 1.5 cap heights, at 8 divisions per module
    em = HEIGHT
    assert cap_h == math.ceil((em + 1.5 * 1.8 / MODULE_MM) * 8 - 1e-9)
    grid_w, grid_h = text_footprint(GRID_FONT, "K1234\nK1", 1.8, GRID)
    assert grid_w == wide_w
    assert grid_h == 2 * one_h
    assert cap_h > one_h
    assert text_footprint(CAP_FONT, "K1234\nK1", 1.8, GRID, turn=True) == (cap_h, cap_w)
