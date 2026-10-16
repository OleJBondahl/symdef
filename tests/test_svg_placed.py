"""`to_placed_fragment`: the oriented mm fragment inside a translate read from the grid (D83)."""

import pytest
from test_measure import EIGHT, FOUR, WIDE

from symdef.errors import UnknownNameError
from symdef.geometry import Weight
from symdef.gridtypes import GridPoint
from symdef.orient import Orientation, orient
from symdef.svg_mm import to_fragment_mm
from symdef.svg_placed import to_placed_fragment

AT = GridPoint(12, -5)


def mm(**over):
    """Return the mm keywords of a draw call, with `over` replacing some."""
    base = {
        "module_mm": 2.5,
        "weights_mm": {Weight.NORMAL: 0.25, Weight.THICK: 0.5},
        "dash_mm": (1.0, 0.5),
        "font_family": "Arial",
        "font_mm": 2.0,
        "cap_ratio": 0.7,
    }
    return {**base, **over}


@pytest.mark.parametrize("orientation", list(Orientation))
def test_the_fragment_is_the_oriented_mm_fragment_inside_a_translate(orientation):
    expected = (
        '<g transform="translate(3.75 -1.5625)">\n'
        + to_fragment_mm(orient(WIDE, orientation), texts={"tag": "A"}, **mm())
        + "</g>\n"
    )
    assert to_placed_fragment(WIDE, orientation, AT, EIGHT, texts={"tag": "A"}, **mm()) == expected


def test_a_grid_of_four_divisions_and_the_module_move_the_translate():
    out = to_placed_fragment(WIDE, Orientation.R0, AT, FOUR, **mm())
    assert out.startswith('<g transform="translate(7.5 -3.125)">\n')
    big = to_placed_fragment(WIDE, Orientation.R0, AT, EIGHT, **mm(module_mm=5.0))
    assert big.startswith('<g transform="translate(7.5 -3.125)">\n')


def test_the_options_pass_through_and_a_bad_text_key_raises():
    out = to_placed_fragment(WIDE, Orientation.R0, GridPoint(0, 0), EIGHT, muted="#888", **mm())
    assert (
        out == f'<g transform="translate(0 0)">\n{to_fragment_mm(WIDE, muted="#888", **mm())}</g>\n'
    )
    with pytest.raises(UnknownNameError, match="nope"):
        to_placed_fragment(WIDE, Orientation.R0, AT, EIGHT, texts={"nope": "x"}, **mm())
