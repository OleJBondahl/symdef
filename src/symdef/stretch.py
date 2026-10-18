"""Stretch a symbol along one axis: every point beyond its cut line moves."""

from collections.abc import Callable, Mapping
from dataclasses import replace
from math import floor
from typing import Literal

from symdef.boxes import body_box, element_box
from symdef.errors import InvalidValueError
from symdef.geometry import Arc, Circle, Direction, Element, Line, Point, Polyline, Text
from symdef.model import Slot, Stretch, Symbol
from symdef.stretch_slot import stretch_slot
from symdef.units import Grid

type Axis = Literal["x", "y"]

_MARKING = "marking."
_WHOLE_TOL = 1e-9  # a growth within this of a whole division counts as whole
# A named port stands on an edge parallel to the axis: its outward normal is across the axis.
_EDGE_NORMALS: dict[str, tuple[Direction, Direction]] = {
    "x": (Direction.N, Direction.S),
    "y": (Direction.E, Direction.W),
}


def _coord(point: Point, axis: Axis) -> float:
    """Return the point's coordinate along the axis."""
    return point.x if axis == "x" else point.y


def _add(point: Point, axis: Axis, delta: float) -> Point:
    """Return the point moved by `delta` along the axis."""
    return Point(point.x + delta, point.y) if axis == "x" else Point(point.x, point.y + delta)


def _span(element: Element, axis: Axis) -> tuple[float, float]:
    """Return the element's extent along the axis as (low, high)."""
    box = element_box(element)
    return (box.min.x, box.max.x) if axis == "x" else (box.min.y, box.max.y)


def crosses_cut(element: Element, axis: Axis, at: float) -> bool:
    """Return whether a circle, arc or text lies on both sides of a cut line.

    A line or polyline may cross a cut (it gets longer), so it never does. Touching the cut from
    one side is not crossing.
    """
    if not isinstance(element, Circle | Arc | Text):
        return False
    low, high = _span(element, axis)
    return low < at < high


def _nudge(element: Circle | Arc | Text, axis: Axis, delta: float) -> Element:
    """Return a circle, arc or text moved whole by `delta` along the axis."""
    if isinstance(element, Text):
        return replace(element, position=_add(element.position, axis, delta))
    return replace(element, center=_add(element.center, axis, delta))


def _stretch_element(
    element: Element, axis: Axis, cuts: tuple[Stretch, ...], shift: Callable[[float], float]
) -> Element:
    """Return the element with its points moved by their shifts; a whole shape moves or stays."""
    match element:
        case Line(start=start, end=end):
            return replace(element, start=_move(start, axis, shift), end=_move(end, axis, shift))
        case Polyline(points=points):
            return replace(element, points=tuple(_move(p, axis, shift) for p in points))
    for cut in cuts:
        if crosses_cut(element, axis, cut.at):
            msg = (
                f"a {type(element).__name__.lower()} crosses the cut at {cut.at} on the {axis} axis"
            )
            raise InvalidValueError(msg)
    delta = shift(_span(element, axis)[1])
    return _nudge(element, axis, delta) if delta else element


def _move(point: Point, axis: Axis, shift: Callable[[float], float]) -> Point:
    """Return the point moved by the shift of its coordinate."""
    delta = shift(_coord(point, axis))
    return _add(point, axis, delta) if delta else point


def _whole_shares(
    cuts: tuple[Stretch, ...], delta: float, grid: Grid, name: str
) -> tuple[float, ...]:
    """Return each cut's share in whole divisions: near cuts floor their weighted share."""
    divisions = delta / grid.division
    if abs(divisions - round(divisions)) > _WHOLE_TOL:
        msg = (
            f"{name}: the growth {delta} is not a whole number of divisions of {grid.division}; "
            "pass a length that is a whole number of divisions"
        )
        raise InvalidValueError(msg)
    total, whole = sum(c.weight for c in cuts), round(divisions)
    near = [floor(whole * c.weight / total + _WHOLE_TOL) for c in cuts[:-1]]
    return tuple(n * grid.division for n in (*near, whole - sum(near)))


def _shift(
    cuts: tuple[Stretch, ...], delta: float, grid: Grid | None = None, name: str = ""
) -> Callable[[float], float]:
    """Return the shift of a coordinate: the shares of the cuts it lies beyond, summed.

    One cut takes `delta` whole, so a single-cut result is the 0.9.0 one to the byte.
    """
    total = sum(c.weight for c in cuts)
    if grid is not None and grid.stretch_split == "whole":
        shares = _whole_shares(cuts, delta, grid, name)
    else:
        shares = (delta,) if len(cuts) == 1 else tuple(delta * c.weight / total for c in cuts)

    def shift(coord: float) -> float:
        return sum((share for c, share in zip(cuts, shares, strict=True) if coord > c.at), 0.0)

    return shift


def _move_offsets(symbol: Symbol, axis: Axis, offsets: Mapping[str, float]) -> Symbol:
    """Place each named port at its offset, with its bound lead and `marking.<port>` slot."""
    shift = {
        p.id: offsets[p.id] - _coord(p.position, axis) for p in symbol.ports if p.id in offsets
    }

    def lead(element: Element) -> Element:
        if isinstance(element, Line) and element.port in shift:
            d = shift[element.port]
            return replace(
                element, start=_add(element.start, axis, d), end=_add(element.end, axis, d)
            )
        return element

    def slot(s: Slot) -> Slot:
        d = shift.get(s.id.removeprefix(_MARKING), 0) if s.id.startswith(_MARKING) else 0
        return replace(s, position=_add(s.position, axis, d))

    return replace(
        symbol,
        elements=tuple(lead(e) for e in symbol.elements),
        ports=tuple(
            replace(p, position=_add(p.position, axis, shift.get(p.id, 0))) for p in symbol.ports
        ),
        slots=tuple(slot(s) for s in symbol.slots),
    )


def _check_offsets(
    symbol: Symbol, axis: Axis, low: float, length: float, offsets: Mapping[str, float]
) -> None:
    """Raise `InvalidValueError` for an offset naming no port, another edge or a bad place."""
    ports = {p.id: p for p in symbol.ports}
    for port_id, value in offsets.items():
        if port_id not in ports:
            msg = f"offsets name the port {port_id!r}, which the symbol does not have"
            raise InvalidValueError(msg)
        if ports[port_id].direction not in _EDGE_NORMALS[axis]:
            msg = f"the port {port_id!r} is not on an edge parallel to the {axis} axis"
            raise InvalidValueError(msg)
        if not low <= value <= low + length:
            msg = f"the offset {value!r} of port {port_id!r} lies outside the stretched body"
            raise InvalidValueError(msg)
        if not float(value).is_integer():
            msg = f"the offset {value!r} of port {port_id!r} is off the 1 M wiring grid"
            raise InvalidValueError(msg)


def stretch(
    symbol: Symbol,
    axis: Axis,
    length: float,
    offsets: Mapping[str, float] | None = None,
    *,
    grid: Grid | None = None,
) -> Symbol:
    """Return the symbol grown along an axis to a body extent of `length`.

    The growth, `length` minus the natural extent, is shared among the axis's cuts in proportion
    to their weights. A point moves by the shares of the cuts it lies beyond: element points,
    ports, anchors and slot corners. A line or polyline segment across a cut gets longer by that
    cut's share; a slot box across one grows the same way. `offsets` then places each named port
    at its coordinate along the axis, with its bound lead and its `marking.<port>` slot; the port
    must stand on an edge parallel to the axis, on the 1 M wiring grid, inside the stretched body.
    The result has no stretch on that axis. With a `grid` whose `stretch_split` is "whole" (D97),
    the growth must be a whole number of divisions and splits in whole divisions: each cut but the
    last, by position along the axis, takes the floor of its weighted share, the last the rest.

    Args:
        symbol: A symbol in base orientation with a stretch on `axis`.
        axis: "x" or "y".
        length: The new body extent along the axis, in module units; the natural extent at least.
        offsets: Port id to coordinate along the axis, or None.
        grid: The library's grid, or None for the weighted split.

    Returns:
        An ordinary symbol; orient it afterwards.

    Raises:
        InvalidValueError: If the symbol has no stretch on the axis, `length` is below the natural
            extent, a circle, arc or text crosses a cut, an offset names no port or a port on
            another edge, or an offset lies outside the stretched body or off the grid, or the grid
            splits in whole divisions and the growth is not a whole number of them.
    """
    cuts = tuple(sorted((s for s in symbol.stretch if s.axis == axis), key=lambda s: s.at))
    if not cuts:
        msg = f"the symbol has no stretch on the {axis} axis"
        raise InvalidValueError(msg)
    box = body_box(symbol)
    low, natural = (box.min.x, box.width) if axis == "x" else (box.min.y, box.height)
    if length < natural:
        msg = f"the length {length} is below the natural extent {natural}"
        raise InvalidValueError(msg)
    _check_offsets(symbol, axis, low, length, offsets or {})
    shift = _shift(cuts, length - natural, grid, symbol.name)
    stretched = replace(
        symbol,
        elements=tuple(_stretch_element(e, axis, cuts, shift) for e in symbol.elements),
        ports=tuple(replace(p, position=_move(p.position, axis, shift)) for p in symbol.ports),
        anchors=tuple(replace(a, position=_move(a.position, axis, shift)) for a in symbol.anchors),
        slots=tuple(stretch_slot(s, axis, shift) for s in symbol.slots),
        stretch=tuple(s for s in symbol.stretch if s.axis != axis),
    )
    return _move_offsets(stretched, axis, offsets or {})
