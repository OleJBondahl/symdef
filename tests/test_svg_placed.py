"""`to_placed_fragment`: the oriented fragment inside a translate read from the grid (D83)."""

from dataclasses import replace

import pytest
from test_measure import EIGHT, FOUR, WIDE

from symdef.errors import UnknownNameError
from symdef.gridtypes import GridPoint
from symdef.orient import Orientation, orient
from symdef.svg import to_fragment
from symdef.svg_placed import to_placed_fragment

AT = GridPoint(12, -5)


@pytest.mark.parametrize("orientation", list(Orientation))
def test_the_fragment_is_the_oriented_fragment_inside_a_translate(orientation):
    expected = (
        '<g transform="translate(1.5 -0.625)">\n'
        + to_fragment(orient(WIDE, orientation), texts={"tag": "A"})
        + "</g>\n"
    )
    assert to_placed_fragment(WIDE, orientation, AT, EIGHT, texts={"tag": "A"}) == expected


def test_a_grid_of_four_divisions_moves_the_translate():
    out = to_placed_fragment(WIDE, Orientation.R0, AT, FOUR)
    assert out.startswith('<g transform="translate(3 -1.25)">\n')
    assert out != to_placed_fragment(WIDE, Orientation.R0, AT, EIGHT)


def test_the_options_pass_through_and_the_float_fragment_is_unchanged():
    out = to_placed_fragment(WIDE, Orientation.R0, GridPoint(0, 0), EIGHT, muted="#888")
    assert out == f'<g transform="translate(0 0)">\n{to_fragment(WIDE, muted="#888")}</g>\n'
    assert "translate" not in to_fragment(WIDE)
    with pytest.raises(UnknownNameError, match="nope"):
        to_placed_fragment(WIDE, Orientation.R0, AT, replace(EIGHT), texts={"nope": "x"})
