"""Library rule: every symbol's keepout holds its ink, body and leads, in each orientation."""

from dataclasses import replace
from pathlib import Path

import pytest
from build_symbol import plain_symbol
from stretch_samples import card, slab

import symdef
from symdef.boxes import ink_boxes, keepout_box
from symdef.geometry import Box, Line, Point, Polyline
from symdef.orient import Orientation, orient
from symdef.stretch import stretch

ROOT = Path(__file__).resolve().parent.parent
SETS = (
    ROOT / "docs" / "tutorial-set",
    ROOT / "tests" / "fixtures" / "guide",
    ROOT / "tests" / "fixtures" / "pipe",
)


def ink_outside_keepout(symbol, font=None):
    """Return the ink boxes (body and leads) the symbol's keepout does not hold."""
    ink = ink_boxes(symbol, font=font)
    keepout = keepout_box(symbol, font)
    boxes = (*(() if ink.body is None else (ink.body,)), *ink.leads)
    return [b for b in boxes if Box.union(keepout, b) != keepout]


def shipped():
    for root in SETS:
        library = symdef.load_library(root)
        for name, symbol in library.symbols.items():
            yield pytest.param(symbol, library.font, id=f"{root.name}-{name}")
    yield pytest.param(stretch(card(), "x", 64), None, id="card-stretched")
    yield pytest.param(stretch(slab(), "x", 32), None, id="slab-stretched-x")


@pytest.mark.parametrize(("symbol", "font"), list(shipped()))
@pytest.mark.parametrize("orientation", list(Orientation))
def test_every_keepout_holds_the_ink(symbol, font, orientation):
    assert ink_outside_keepout(orient(symbol, orientation), font) == []


def test_a_declared_keepout_smaller_than_the_ink_is_found():
    body = Polyline((Point(0, 0), Point(10, 0), Point(10, 4), Point(0, 4)), closed=True)
    lead = Line(Point(10, 2), Point(14, 2), port="out")
    symbol = plain_symbol(elements=(body, lead), keepout=Box(Point(0, 0), Point(10, 4)))
    assert ink_outside_keepout(symbol) == [Box(Point(10, 2), Point(14, 2))]
    assert ink_outside_keepout(replace(symbol, keepout=Box(Point(0, 0), Point(14, 4)))) == []
