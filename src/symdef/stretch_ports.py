"""The length and offsets that make one edge of a stretched symbol carry n ports on the pitch."""

from collections.abc import Callable, Sequence

from symdef.boxes import body_box
from symdef.edge_pattern import pattern_coords
from symdef.errors import InvalidValueError
from symdef.geometry import Direction
from symdef.model import Port, Symbol
from symdef.repeat import MAX_REPEAT
from symdef.stretch import _EDGE_NORMALS, Axis
from symdef.units import DEFAULT_GRID, Grid, from_divisions


def _along(port: Port, axis: Axis) -> float:
    """Return the port's coordinate along the axis."""
    return port.position.x if axis == "x" else port.position.y


def _edge_ports(symbol: Symbol, axis: Axis, edge: Direction, n: int) -> list[Port]:
    """Return the ports declared on `edge`, in order along the axis; raise if n cannot be met."""
    if edge not in _EDGE_NORMALS[axis]:
        msg = f"{symbol.name}: the edge {edge.name} is not parallel to the {axis} axis"
        raise InvalidValueError(msg)
    if not any(cut.axis == axis for cut in symbol.stretch):
        msg = (
            f"{symbol.name}: no stretch on the {axis} axis, so edge {edge.name} "
            f"cannot be stretched to n={n} ports; declare a cut on that axis"
        )
        raise InvalidValueError(msg)
    ports = sorted((p for p in symbol.ports if p.direction is edge), key=lambda p: _along(p, axis))
    limit = MAX_REPEAT if any(p.pattern for p in ports) else len(ports)
    if not 1 <= n <= limit:
        msg = (
            f"{symbol.name}: edge {edge.name} cannot carry n={n} ports; "
            f"it declares {limit}; ask for 1 to {limit}"
        )
        raise InvalidValueError(msg)
    return ports


def _pattern_edge(
    symbol: Symbol, axis: Axis, ports: list[Port], coords_of: Callable[[float], list[float]]
) -> tuple[float, dict[str, float]]:
    """Return the length and offsets for an edge with a pattern port, named ports kept apart."""
    pattern = next(p for p in ports if p.pattern)
    declared = _along(pattern, axis)
    coords = coords_of(declared)
    grow = max(0, coords[-1] - declared)
    offsets = {
        p.id: coords[0]
        if p is pattern
        else _along(p, axis) + (grow if _along(p, axis) > declared else 0)
        for p in ports
    }
    box = body_box(symbol)
    return (box.width if axis == "x" else box.height) + grow, offsets


def stretch_to_ports(  # noqa: PLR0913 - the ruled signature: symbol, axis, edge, n, grid and two options
    symbol: Symbol,
    axis: Axis,
    edge: Direction,
    n: int,
    *,
    grid: Grid = DEFAULT_GRID,
    pitch: float | None = None,
    positions: Sequence[float] | None = None,
) -> tuple[float, dict[str, float]]:
    """Return the `length` and `offsets` for `stretch` so that `edge` carries n ports on the pitch.

    The n ports are the first n declared on the edge, in order along the axis. The first keeps
    its coordinate and the rest follow at the grid's standard wire pitch (`wire_pitch`, in
    module units). The ends keep the margins the symbol declares: from the body's low side to
    the first port, and from the last declared port to its high side. The length is the span
    those give, never below the natural extent, so `stretch(symbol, axis, length, offsets,
    grid=grid)` is valid. Call `only_ports` first so the edge holds only the ports you wire.

    An edge with a pattern port (`pattern_ports`) takes any n up to MAX_REPEAT, counting copies
    of that port only. The offsets hold every port on the edge: those before the pattern port keep
    their coordinate, the pattern port goes to the first copy, those after it move by the growth
    of the copies' span. The length grows by that span. `pitch` (a whole multiple of the wire
    pitch) or `positions` (n increasing coordinates) place the copies as in `pattern_ports`, and
    apply to a pattern edge only. Run `stretch`, then `pattern_ports` with the same arguments.

    Raises:
        InvalidValueError: If the symbol has no stretch on the axis, `edge` is not parallel to
            the axis, n is below 1 or above the ports declared on the edge (MAX_REPEAT on a
            pattern edge), `pitch` or `positions` is malformed or given for an edge with no
            pattern port; the message names the symbol, the edge and the fix.
    """
    ports = _edge_ports(symbol, axis, edge, n)
    if any(p.pattern for p in ports):
        return _pattern_edge(
            symbol,
            axis,
            ports,
            lambda first: pattern_coords(symbol, first, n, grid, pitch, positions),
        )
    if pitch is not None or positions is not None:
        msg = (
            f"{symbol.name}: pitch and positions apply to a pattern edge only; "
            f"edge {edge.name} has no pattern port"
        )
        raise InvalidValueError(msg)
    wire = from_divisions(grid, grid.wire_pitch)
    box = body_box(symbol)
    low, high = (box.min.x, box.max.x) if axis == "x" else (box.min.y, box.max.y)
    first, last = _along(ports[0], axis), _along(ports[-1], axis)
    length = max(high - low, (first - low) + (n - 1) * wire + (high - last))
    return length, {p.id: first + i * wire for i, p in enumerate(ports[:n])}
