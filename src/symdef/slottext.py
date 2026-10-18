"""Where a string drawn in a slot sits, and the room it takes there."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Literal

from symdef.font import FontMetrics, cap_height, text_width
from symdef.geometry import Box, Direction, Point
from symdef.model import Centre, Slot
from symdef.units import DEFAULT_GRID, Grid, ceil_divisions, from_divisions

type Anchor = Literal["start", "middle", "end"]

# Per slot side: the text anchor and the baseline below the slot point as a fraction of the cap
# height. `slot_text` and the SVG output read this one table (D63).
SIDE_ALIGN: Mapping[Direction | Centre, tuple[Anchor, float]] = MappingProxyType(
    {
        Direction.E: ("start", 0.5),
        Direction.W: ("end", 0.5),
        Direction.N: ("middle", 0.0),
        Direction.S: ("middle", 1.0),
        Centre.C: ("middle", 0.5),
    }
)
# A turned slot reads bottom-up: N starts at the anchor, S ends there, E and W centre the text on
# it. The second number is how far east of the slot point the baseline sits, in cap heights.
TURNED_ALIGN: Mapping[Direction | Centre, tuple[Anchor, float]] = MappingProxyType(
    {
        Direction.N: ("start", 0.5),
        Direction.S: ("end", 0.5),
        Direction.E: ("middle", 1.0),
        Direction.W: ("middle", 0.0),
        Centre.C: ("middle", 0.5),
    }
)


@dataclass(frozen=True, slots=True)
class TextPlacement:
    """Where a slot's string is drawn.

    Attributes:
        point: The baseline point the text is anchored at, in module units.
        anchor: Which end of the text sits on `point`: `start`, `middle` or `end`.
        turned: True when the text reads bottom-up, rotated a quarter turn counter-clockwise about
            `point`.
    """

    point: Point
    anchor: Anchor
    turned: bool


def _base(slot: Slot, height: float, font: FontMetrics | None) -> TextPlacement:
    """Return where a one-line string of text height `height` is drawn in a slot, by the cap rule.

    The side picks the anchor and the baseline from `SIDE_ALIGN`, or from `TURNED_ALIGN` when the
    slot is turned; the shifts are in cap heights, which `font` gives (0.72 em with no font). The
    point does not depend on the string, because the anchor does the aligning.
    """
    cap = cap_height(font, height)
    if slot.turn:
        anchor, east = TURNED_ALIGN[slot.side]
        return TextPlacement(
            Point(slot.position.x + east * cap, slot.position.y), anchor, turned=True
        )
    anchor, south = SIDE_ALIGN[slot.side]
    return TextPlacement(
        Point(slot.position.x, slot.position.y + south * cap), anchor, turned=False
    )


def slot_text(
    slot: Slot,
    text: str,  # noqa: ARG001 - the anchor, not the length, aligns a text, so none moves the point
    height: float,
    font: FontMetrics | None,
    grid: Grid = DEFAULT_GRID,
) -> TextPlacement:
    """Return where a string of text height `height` is drawn in a slot, as one line (D95).

    The font's `text_block` rule sets the baseline: "cap" from `SIDE_ALIGN` and `TURNED_ALIGN`,
    "grid" as a one-row block (`slot_lines`, `grid` gives the divisions).
    """
    return slot_lines(slot, "", height, font, grid)[0]


def _span(anchor: Anchor, at: float, length: float) -> tuple[float, float]:
    """Return the interval of `length` that `anchor` puts around the coordinate `at`."""
    match anchor:
        case "start":
            return at, at + length
        case "middle":
            return at - length / 2, at + length / 2
        case "end":
            return at - length, at


# Rows of a multi-line text sit this many cap heights apart: one cap height and half of one more.
LINE_PITCH = 1.5


def _before(slot: Slot) -> float:
    """Return the share of a text block before the slot point: it grows away from its side (D95)."""
    if slot.side is (Direction.W if slot.turn else Direction.N):
        return 1.0
    return 0.0 if slot.side is (Direction.E if slot.turn else Direction.S) else 0.5


def stack_shifts(slot: Slot, count: int) -> tuple[float, ...]:
    """Return each of `count` lines' shift from a single line's baseline, in cap heights (D95)."""
    before = _before(slot) * (count - 1)
    return tuple(LINE_PITCH * (i - before) for i in range(count))


def _grid_block(
    slot: Slot, count: int, height: float, font: FontMetrics, grid: Grid
) -> list[float]:
    """Return each baseline by the "grid" rule: rows of `height` rounded up, top snapped down."""
    pitch = from_divisions(grid, ceil_divisions(grid, height))
    at = slot.position.x if slot.turn else slot.position.y
    top = math.floor((at - _before(slot) * count * pitch) / grid.division + 1e-9) * grid.division
    return [top + i * pitch + font.ascent / font.units_per_em * height for i in range(count)]


def slot_lines(
    slot: Slot, text: str, height: float, font: FontMetrics | None, grid: Grid = DEFAULT_GRID
) -> tuple[TextPlacement, ...]:
    """Return one placement for each newline-separated line of a text (D95).

    The font's `text_block` rule sets the rows: "cap" puts them `LINE_PITCH` cap heights apart,
    "grid" a whole number of `grid` divisions apart.
    """
    first = _base(slot, height, font)
    count, turned = len(text.split("\n")), first.turned
    if font is not None and font.text_block == "grid":
        rows = _grid_block(slot, count, height, font, grid)
    else:
        start = first.point.x if turned else first.point.y
        rows = [start + shift * cap_height(font, height) for shift in stack_shifts(slot, count)]
    return tuple(
        replace(first, point=Point(r, first.point.y) if turned else Point(first.point.x, r))
        for r in rows
    )


def _line_box(placement: TextPlacement, width: float, back: float, ahead: float) -> Box:
    """Return the box of one line drawn at its placement, `back` behind its baseline."""
    x, y = placement.point.x, placement.point.y
    if placement.turned:
        low, high = _span(placement.anchor, -y, width)
        return Box(Point(x - back, -high), Point(x + ahead, -low))
    left, right = _span(placement.anchor, x, width)
    return Box(Point(left, y - back), Point(right, y + ahead))


def text_box(
    slot: Slot, text: str, height: float, font: FontMetrics | None, grid: Grid = DEFAULT_GRID
) -> Box:
    """Return the extent of a string drawn in a slot: the union of its lines' boxes.

    By "cap" a line is its width by one cap height; by "grid" a whole row, an ascent behind the
    baseline and the rest ahead.
    """
    back, ahead = cap_height(font, height), 0.0
    if font is not None and font.text_block == "grid":
        back = font.ascent / font.units_per_em * height
        ahead = from_divisions(grid, ceil_divisions(grid, height)) - back
    placed = slot_lines(slot, text, height, font, grid)
    return Box.union(
        *(
            _line_box(p, text_width(font, t, height), back, ahead)
            for p, t in zip(placed, text.split("\n"), strict=True)
        )
    )
