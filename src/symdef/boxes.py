"""The body, slot and keep-out boxes of a symbol."""

import math

from symdef.errors import InvalidValueError
from symdef.font import FontMetrics, text_width
from symdef.geometry import (
    Arc,
    Box,
    Circle,
    Direction,
    Element,
    Line,
    Point,
    Polyline,
    Text,
    arc_point,
    arc_sweep,
)
from symdef.model import Centre, Slot, Symbol
from symdef.slottext import text_box
from symdef.units import DEFAULT_GRID, Grid

_AXIS_ANGLES = (0, 90, 180, 270)
_FULL_TURN = 360
_ORIGIN_BOX = Box(Point(0, 0), Point(0, 0))


def _extent_points(element: Element, font: FontMetrics | None = None) -> tuple[Point, ...]:
    """Return points whose bounding box is the element's extent, ignoring stroke width.

    An arc with a non-finite angle has no swept extent and counts as its centre.
    """
    match element:
        case Line(start=start, end=end):
            return (start, end)
        case Polyline(points=points):
            return points
        case Circle(center=c, radius=r):
            return (Point(c.x - r, c.y - r), Point(c.x + r, c.y + r))
        case Arc() as arc:
            if not (math.isfinite(arc.start_deg) and math.isfinite(arc.end_deg)):
                return (arc.center,)
            start, end = arc.start_deg % _FULL_TURN, arc.end_deg % _FULL_TURN
            sweep = arc_sweep(arc)
            extremes = tuple(a for a in _AXIS_ANGLES if (a - start) % _FULL_TURN <= sweep)
            return tuple(arc_point(arc, a) for a in (start, end, *extremes))
        case Text(content=content, position=at, height=height, weight=weight):
            half_w = text_width(font, content, height, weight) / 2
            return (
                Point(at.x - half_w, at.y - height / 2),
                Point(at.x + half_w, at.y + height / 2),
            )


def _bounding(points: tuple[Point, ...]) -> Box:
    """Return the smallest box holding every point; no points give the origin box."""
    if not points:
        return _ORIGIN_BOX
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return Box(Point(min(xs), min(ys)), Point(max(xs), max(ys)))


def element_box(element: Element, font: FontMetrics | None = None) -> Box:
    """Return the extent of one element.

    A line or polyline extends over its points, a circle over its full diameter, an arc over its
    true swept extent, and text is a box centred on its position, `height` tall and `text_width`
    wide (`0.6 * height` per character when `font` is None). Stroke width is ignored. A polyline
    without points has the origin box.
    """
    return _bounding(_extent_points(element, font))


def elements_box(elements: tuple[Element, ...], font: FontMetrics | None = None) -> Box:
    """Return the box holding every element's extent, as `element_box`; none gives the origin."""
    return _bounding(tuple(p for e in elements for p in _extent_points(e, font)))


def body_box(symbol: Symbol, font: FontMetrics | None = None) -> Box:
    """Return the union of the element extents, in module units, ignoring stroke width.

    Extents are as for text (`text_width` with `font`; with no font `0.6 * height` per character),
    arcs (the true swept extent) and the other elements. A symbol without elements has the box
    (0, 0) to (0, 0). Ports, anchors and slots do not count.

    A symbol that declares its `body` (D98) has exactly that box, whatever its elements and
    `font`.
    """
    if symbol.body is not None:
        return symbol.body
    return elements_box(symbol.elements, font)


def slots_box(symbol: Symbol) -> Box:
    """Return the union of the boxes the slots reserve, without the body.

    A symbol without slots has the box (0, 0) to (0, 0).
    """
    boxes = tuple(_reserved_box(slot) for slot in symbol.slots)
    return Box.union(*boxes) if boxes else _bounding(())


def _reserved_box(slot: Slot) -> Box:
    """Return the box a slot reserves; `slot_box` documents its placement."""
    return side_box(slot.position, slot.side, *slot.box)


def side_box(point: Point, side: Direction | Centre, w: float, h: float) -> Box:
    """Return a `w` by `h` box grown from `point` towards `side`, as a slot reserves it.

    E grows right and W left, both centred on y; N grows up and S down, both centred on x; C is
    centred both ways. The box is never rotated.
    """
    x, y = point.x, point.y
    match side:
        case Direction.E:
            return Box(Point(x, y - h / 2), Point(x + w, y + h / 2))
        case Direction.W:
            return Box(Point(x - w, y - h / 2), Point(x, y + h / 2))
        case Direction.N:
            return Box(Point(x - w / 2, y - h), Point(x + w / 2, y))
        case Direction.S:
            return Box(Point(x - w / 2, y), Point(x + w / 2, y + h))
        case Centre.C:
            return Box(Point(x - w / 2, y - h / 2), Point(x + w / 2, y + h / 2))


def slot_box(
    slot: Slot,
    text: str | None = None,
    height: float | None = None,
    font: FontMetrics | None = None,
    grid: Grid = DEFAULT_GRID,
) -> Box:
    """Return the box a slot reserves: it grows from the slot point towards its side.

    E and W grow horizontally and are vertically centred; N grows up and S grows down and both
    are horizontally centred; C is centred on the point both ways. The box is never rotated; only
    the point and side are.

    With a `text` the box also holds that string drawn at text height `height` (`slot_text`
    places it, `font` measures it, 0.6 em per character with no font): the union of the reserved
    box and the string's extent. Without a text it is the reserved box.

    Raises:
        InvalidValueError: If a text is given without a height.
    """
    reserved = _reserved_box(slot)
    if text is None:
        return reserved
    if height is None:
        msg = "slot_box needs a height to measure a text"
        raise InvalidValueError(msg)
    drawn = text_box(slot, text, height, font, grid)
    return _bounding((reserved.min, reserved.max, drawn.min, drawn.max))


def keepout_box(symbol: Symbol, font: FontMetrics | None = None) -> Box:
    """Return the body box united with every slot box: the room the symbol needs kept clear.

    `font` measures the body's text as `body_box` does. A symbol that declares its `keepout` has
    exactly that box; one that declares only a `body` has the declared body united with the slots.
    """
    if symbol.keepout is not None:
        return symbol.keepout
    boxes = (body_box(symbol, font), *(slot_box(s) for s in symbol.slots))
    return _bounding(tuple(p for b in boxes for p in (b.min, b.max)))
