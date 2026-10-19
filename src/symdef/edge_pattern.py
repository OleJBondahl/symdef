"""Expand a pattern port into n ports along its edge at the wire pitch, or a multiple of it."""

from collections.abc import Callable, Sequence
from dataclasses import replace
from itertools import pairwise

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.geometry import Direction, Element, Line, Point
from symdef.model import Port, Slot, Symbol
from symdef.repeat import MAX_REPEAT, pole_port
from symdef.units import DEFAULT_GRID, Grid, from_divisions

_MARKING = "marking."
_TOL = 1e-9  # a distance within this of a whole pitch counts as whole


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


def _whole(symbol: Symbol, what: str, value: float, wire: float) -> None:
    """Raise unless `value` is a whole multiple, at least 1x, of the wire pitch."""
    ratio = value / wire
    if ratio < 1 - _TOL or abs(ratio - round(ratio)) > _TOL:
        msg = (
            f"{symbol.name}: {what} {value:g} is not a whole multiple of the wire pitch "
            f"{wire:g}; use {wire:g}, {2 * wire:g}, {3 * wire:g} and so on"
        )
        raise InvalidValueError(msg)


def _from_positions(symbol: Symbol, n: int, positions: Sequence[float], wire: float) -> list[float]:
    """Return the positions as coordinates after checking their count, order and gaps."""
    coords = list(positions)
    if len(coords) != n:
        msg = (
            f"{symbol.name}: positions holds {len(coords)} coordinates for n={n} copies; "
            f"give exactly {n}"
        )
        raise InvalidValueError(msg)
    for low, high in pairwise(coords):
        if high <= low:
            msg = (
                f"{symbol.name}: positions {coords!r} do not increase; "
                f"list the copies from low to high along the edge"
            )
            raise InvalidValueError(msg)
        _whole(symbol, "the gap between positions", high - low, wire)
    return coords


def pattern_coords(  # noqa: PLR0913, PLR0917 - the symbol, start, count, grid and the two options
    symbol: Symbol,
    first: float,
    n: int,
    grid: Grid,
    pitch: float | None,
    positions: Sequence[float] | None,
) -> list[float]:
    """Return the n coordinates of the copies along the axis; raise if pitch or positions is bad."""
    wire = from_divisions(grid, grid.wire_pitch)
    if pitch is not None and positions is not None:
        msg = f"{symbol.name}: gives both pitch and positions; give one of them"
        raise InvalidValueError(msg)
    if positions is not None:
        return _from_positions(symbol, n, positions, wire)
    if pitch is None:
        pitch = wire
    _whole(symbol, "the pitch", pitch, wire)
    return [first + k * pitch for k in range(n)]


def _check_extent(symbol: Symbol, axis: str, port: Port, coords: list[float]) -> None:
    """Raise if a copy lies outside the body box along the axis."""
    box = body_box(symbol)
    low, high = (box.min.x, box.max.x) if axis == "x" else (box.min.y, box.max.y)
    if coords[0] < low:
        msg = (
            f"{symbol.name}: the first copy of the pattern port {port.id!r} on edge "
            f"{port.direction.name} lies at {coords[0]:g}, before the body's low side {low:g} "
            f"along the {axis} axis; move it inside"
        )
        raise InvalidValueError(msg)
    if coords[-1] > high:
        msg = (
            f"{symbol.name}: {len(coords)} copies of the pattern port {port.id!r} on edge "
            f"{port.direction.name} need a body extent of at least {coords[-1] - low:g} along the "
            f"{axis} axis; stretch it first (stretch_to_ports)"
        )
        raise InvalidValueError(msg)


def _check_clash(symbol: Symbol, axis: str, port: Port, coords: list[float], wire: float) -> None:
    """Raise if a copy lies less than one wire pitch from a named port on the edge."""
    for other in symbol.ports:
        if other is port or other.direction is not port.direction:
            continue
        at = other.position.x if axis == "x" else other.position.y
        for k, c in enumerate(coords, 1):
            if abs(c - at) < wire - _TOL:
                msg = (
                    f"{symbol.name}: the copy {pole_port(k, port.id)!r} at {c:g} lies within one "
                    f"wire pitch {wire:g} of the port {other.id!r} at {at:g} on edge "
                    f"{port.direction.name}; move the port or the copy"
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


def pattern_ports(  # noqa: PLR0913 - the ruled signature: symbol, edge, n, grid and two options
    symbol: Symbol,
    edge: Direction,
    n: int,
    *,
    grid: Grid = DEFAULT_GRID,
    pitch: float | None = None,
    positions: Sequence[float] | None = None,
) -> Symbol:
    """Return the symbol with the pattern port of `edge` expanded into n ports along the edge.

    The port marked `pattern` becomes n copies along the edge (x for N and S, y for E and W): copy
    k, counted from 1, is `k.<id>`. By default it stands k-1 wire pitches (`wire_pitch`, in module
    units) past the original. `pitch` sets the step instead, a whole multiple of the wire pitch;
    `positions` sets the n coordinates, strictly increasing, each gap a whole multiple of the wire
    pitch, each inside the body. Give at most one of them. Each bound lead and `marking.<id>` slot
    is copied and renamed per copy, and the originals go. Named ports on the edge stay put. Call
    it after `stretch`: expanding first would widen the body, as bound leads count in it.

    Raises:
        InvalidValueError: If n is below 1 or above MAX_REPEAT, `edge` has no pattern port, a
            copy lies outside the body or within one wire pitch of a named port, or `pitch` or
            `positions` is malformed; the message names the symbol and the fix.
    """
    port = _pattern_port(symbol, edge, n)
    axis = "x" if edge in (Direction.N, Direction.S) else "y"
    first = port.position.x if axis == "x" else port.position.y
    coords = pattern_coords(symbol, first, n, grid, pitch, positions)
    _check_extent(symbol, axis, port, coords)
    _check_clash(symbol, axis, port, coords, from_divisions(grid, grid.wire_pitch))
    shifts = [(k, c - first) for k, c in enumerate(coords, 1)]
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
