"""Expand a pattern port into n ports along its edge at the wire pitch."""

from collections.abc import Callable
from dataclasses import replace

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.geometry import Direction, Element, Line, Point
from symdef.model import Port, Slot, Symbol
from symdef.repeat import MAX_REPEAT, pole_port
from symdef.units import DEFAULT_GRID, Grid, from_divisions

_MARKING = "marking."


def _shift(point: Point, axis: str, delta: float) -> Point:
    """Return the point moved by `delta` along the axis."""
    return Point(point.x + delta, point.y) if axis == "x" else Point(point.x, point.y + delta)


def _pattern_port(symbol: Symbol, edge: Direction, n: int) -> Port:
    """Return the pattern port of `edge`; raise if n is out of range or the edge has none."""
    if not 1 <= n <= MAX_REPEAT:
        msg = (
            f"{symbol.name}: edge {edge.name} cannot carry n={n} pattern ports; "
            f"ask for 1 to {MAX_REPEAT}"
        )
        raise InvalidValueError(msg)
    for port in symbol.ports:
        if port.direction is edge and port.pattern:
            return port
    msg = (
        f"{symbol.name}: declares no pattern port on edge {edge.name}; "
        "set pattern = true on one port of that edge"
    )
    raise InvalidValueError(msg)


def _check_extent(symbol: Symbol, axis: str, port: Port, n: int, pitch: float) -> None:
    """Raise if the last copy lies beyond the body box's high side on the axis."""
    box = body_box(symbol)
    low, high = (box.min.x, box.max.x) if axis == "x" else (box.min.y, box.max.y)
    first = port.position.x if axis == "x" else port.position.y
    last = first + (n - 1) * pitch
    if last > high:
        msg = (
            f"{symbol.name}: {n} copies of the pattern port {port.id!r} on edge "
            f"{port.direction.name} need a body extent of at least {last - low:g} along the "
            f"{axis} axis; stretch it first (stretch_to_ports)"
        )
        raise InvalidValueError(msg)


def _expand_leads(
    elements: tuple[Element, ...], port_id: str, axis: str, shifts: list[tuple[int, float]]
) -> tuple[Element, ...]:
    """Return the elements with the lead bound to `port_id` replaced by one moved copy per shift."""
    out: list[Element] = []
    for element in elements:
        if isinstance(element, Line) and element.port == port_id:
            out += [
                replace(
                    element,
                    start=_shift(element.start, axis, d),
                    end=_shift(element.end, axis, d),
                    port=pole_port(k, port_id),
                )
                for k, d in shifts
            ]
        else:
            out.append(element)
    return tuple(out)


def _copy_slot(slot: Slot, port_id: str, k: int, axis: str, delta: float) -> Slot:
    """Return the marking slot for copy `k`, moved along the axis."""
    return replace(
        slot, id=_MARKING + pole_port(k, port_id), position=_shift(slot.position, axis, delta)
    )


def _copy_port(port: Port, k: int, axis: str, delta: float) -> Port:
    """Return copy `k` of the port, moved along the axis and no longer a pattern."""
    return replace(
        port, id=pole_port(k, port.id), position=_shift(port.position, axis, delta), pattern=False
    )


def _expand[T](
    items: tuple[T, ...],
    match: Callable[[T], bool],
    make: Callable[[T, int, float], T],
    shifts: list[tuple[int, float]],
) -> tuple[T, ...]:
    """Return the items with each match replaced, in place, by one `make` result per shift."""
    return tuple(
        out
        for item in items
        for out in ([make(item, k, d) for k, d in shifts] if match(item) else [item])
    )


def pattern_ports(symbol: Symbol, edge: Direction, n: int, *, grid: Grid = DEFAULT_GRID) -> Symbol:
    """Return the symbol with the pattern port of `edge` expanded into n ports on the wire pitch.

    The port marked `pattern` becomes n copies along the edge (x for N and S, y for E and W): copy
    k, counted from 1, is `k.<id>`, k-1 pitches past the original (`wire_pitch`, in module units).
    Its bound lead and its `marking.<id>` slot are copied and renamed per copy, and the originals
    go. Call it after `stretch`: expanding first would widen the body, as bound leads count in it.

    Raises:
        InvalidValueError: If n is below 1 or above MAX_REPEAT, `edge` has no pattern port, or
            the last copy lies past the body's high side; the message names the symbol, edge, n.
    """
    port = _pattern_port(symbol, edge, n)
    axis = "x" if edge in (Direction.N, Direction.S) else "y"
    pitch = from_divisions(grid, grid.wire_pitch)
    _check_extent(symbol, axis, port, n, pitch)
    shifts = [(k, (k - 1) * pitch) for k in range(1, n + 1)]
    marking = _MARKING + port.id
    return replace(
        symbol,
        ports=_expand(
            symbol.ports, lambda p: p is port, lambda p, k, d: _copy_port(p, k, axis, d), shifts
        ),
        elements=_expand_leads(symbol.elements, port.id, axis, shifts),
        slots=_expand(
            symbol.slots,
            lambda s: s.id == marking,
            lambda s, k, d: _copy_slot(s, port.id, k, axis, d),
            shifts,
        ),
    )
