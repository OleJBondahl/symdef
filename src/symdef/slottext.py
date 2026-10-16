"""Where a string drawn in a slot sits, and the room it takes there."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from symdef.font import FontMetrics, cap_height, text_width
from symdef.geometry import Box, Direction, Point
from symdef.model import Centre, Slot

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


def slot_text(
    slot: Slot,
    text: str,  # noqa: ARG001 - the anchor, not the length, aligns a text, so none moves the point
    height: float,
    font: FontMetrics | None,
) -> TextPlacement:
    """Return where a string of text height `height` is drawn in a slot.

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


def _span(anchor: Anchor, at: float, length: float) -> tuple[float, float]:
    """Return the interval of `length` that `anchor` puts around the coordinate `at`."""
    match anchor:
        case "start":
            return at, at + length
        case "middle":
            return at - length / 2, at + length / 2
        case "end":
            return at - length, at


def text_box(slot: Slot, text: str, height: float, font: FontMetrics | None) -> Box:
    """Return the extent of a string drawn in a slot: its measured width by one cap height.

    An upright text runs east from `start`, a turned one runs up from it; the caps stand above the
    baseline, and a turned text's caps stand to the west of it.
    """
    placement = slot_text(slot, text, height, font)
    width, cap = text_width(font, text, height), cap_height(font, height)
    x, y = placement.point.x, placement.point.y
    if placement.turned:
        low, high = _span(placement.anchor, -y, width)
        return Box(Point(x - cap, -high), Point(x, -low))
    left, right = _span(placement.anchor, x, width)
    return Box(Point(left, y - cap), Point(right, y))
