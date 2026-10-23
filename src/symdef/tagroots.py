"""`tag_roots`: where a text starts at the corners of a symbol's tag slot, in grid divisions."""

import math
from dataclasses import dataclass
from typing import Literal

from symdef.errors import InvalidValueError, UnknownNameError
from symdef.geometry import Direction
from symdef.gridmeasure import Measure, measure
from symdef.gridtypes import GridBox
from symdef.model import Library, Slot, Symbol
from symdef.orient import Orientation, orient
from symdef.repeat import pole_pitch
from symdef.slottext import slot_text

_MARKING = "marking."


@dataclass(frozen=True, slots=True)
class TextRoot:
    """A point where a text starts, in whole grid divisions, y down.

    Attributes:
        x: The point's horizontal position.
        y: The point's vertical position.
        h: The text's horizontal alignment at the point; `"right"` means it extends to the left.
        v: The text's vertical alignment at the point: `"baseline"`, or `"top"` for a text that
            hangs below it.
    """

    x: int
    y: int
    h: Literal["left", "right"]
    v: Literal["baseline", "top"]


def _round(library: Library, value: float) -> int:
    """Return `value` module units as whole divisions, to the nearest, halves up."""
    return math.floor(value * library.grid.divisions_per_module + 0.5)


def _baseline(slot: Slot, marking_height: float, library: Library) -> int:
    """Return the baseline `slot_text` sets a text on in `slot`, in divisions."""
    placed = slot_text(slot, "", marking_height, library.font, library.grid)
    return _round(library, placed.point.y)


def _inside(inner: GridBox, outer: GridBox) -> bool:
    """Return whether `inner` lies wholly within `outer`."""
    return (
        outer.min.x <= inner.min.x
        and outer.min.y <= inner.min.y
        and inner.max.x <= outer.max.x
        and inner.max.y <= outer.max.y
    )


def _own_root(slot: Slot, box: GridBox, marking_height: float, library: Library) -> TextRoot:
    """Return the root of a tag slot that lies inside the body: its start edge and baseline."""
    west = slot.side is Direction.W
    return TextRoot(
        box.max.x if west else box.min.x,
        _baseline(slot, marking_height, library),
        "right" if west else "left",
        "baseline",
    )


def _top_left(
    turned: Symbol, measured: Measure, gap: int, marking_height: float, library: Library
) -> TextRoot:
    """Return the root before the mirrors: beside the leftmost top port, else above the body."""
    body = measured.body
    top = [p for p in measured.ports.values() if p.direction is Direction.N]
    if not top:
        return TextRoot(body.min.x, body.min.y - gap, "left", "baseline")
    port = min(top, key=lambda p: p.x)
    slot = next((s for s in turned.slots if s.id == _MARKING + port.id), None)
    y = body.min.y if slot is None else _baseline(slot, marking_height, library)
    x = port.x - gap
    if body.min.x <= x <= body.max.x and body.min.y < y < body.max.y:
        y = body.min.y
    return TextRoot(x, y, "right", "baseline")


def _mirrors(root: TextRoot, body: GridBox) -> tuple[TextRoot, TextRoot, TextRoot, TextRoot]:
    """Return the root, then its reflections through the body centre: BL, TR, BR."""
    sx, sy = body.min.x + body.max.x, body.min.y + body.max.y
    flip_h = "left" if root.h == "right" else "right"
    flip_v = "top" if root.v == "baseline" else "baseline"
    return (
        root,
        TextRoot(root.x, sy - root.y, root.h, flip_v),
        TextRoot(sx - root.x, root.y, flip_h, root.v),
        TextRoot(sx - root.x, sy - root.y, flip_h, flip_v),
    )


def tag_roots(
    symbol: Symbol,
    orientation: Orientation,
    library: Library,
    *,
    gap: float,
    marking_height: float,
) -> tuple[TextRoot, TextRoot, TextRoot, TextRoot]:
    """Return the text root of the symbol's tag slot and its three reflections.

    The roots are `TextRoot`s in whole divisions of `library.grid`, in the frame `measure` uses,
    in the order top-left, bottom-left, top-right, bottom-right. The top-left root is the text
    root of the `tag` slot. When a port leaves the top edge of the body, the point is `gap` to
    the left of the leftmost such port and level with the baseline on which symdef sets a text
    in that port's `marking.<port>` slot; if that point lies inside the body, it is lifted to
    the body's top edge. With no such port, the point is the body's left edge, `gap` above its
    top edge. A `tag` slot lying wholly inside the body gives that slot's start edge and baseline
    in all four. The other three roots reflect the first through the body's centre, left-right,
    top-bottom or both, and each reflection swaps `"right"` with `"left"` or `"baseline"` with
    `"top"`, so a reflected text hangs away from the body as the original does.

    `gap` is in pole units: it is multiplied by `pole_pitch(symbol)` and by
    `library.grid.divisions_per_module`, and rounded to the nearest whole division, halves up.
    `marking_height` is the height `slot_text` takes, for the text in a `marking.<port>` slot
    and for the text in a `tag` slot lying inside the body.

    Raises:
        UnknownNameError: If the symbol has no `tag` slot.
        InvalidValueError: If `gap` is negative or `marking_height` is not above zero.
    """
    if gap < 0:
        msg = f"tag_roots: gap {gap!r} is negative; give a gap of zero or more pole units"
        raise InvalidValueError(msg)
    if not marking_height > 0:
        msg = f"tag_roots: marking_height {marking_height!r} is not above zero; give millimetres"
        raise InvalidValueError(msg)
    turned = orient(symbol, orientation)
    tag = next((s for s in turned.slots if s.id == "tag"), None)
    if tag is None:
        msg = f"tag_roots: symbol {symbol.name!r} has no slot 'tag'; add one"
        raise UnknownNameError(msg)
    measured = measure(symbol, orientation, library)
    if _inside(measured.slots["tag"], measured.body):
        own = _own_root(tag, measured.slots["tag"], marking_height, library)
        return (own, own, own, own)
    divisions = _round(library, gap * pole_pitch(symbol))
    return _mirrors(_top_left(turned, measured, divisions, marking_height, library), measured.body)
