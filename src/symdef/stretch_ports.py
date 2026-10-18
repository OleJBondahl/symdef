"""The length and offsets that make one edge of a stretched symbol carry n ports on the pitch."""

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.geometry import Direction
from symdef.model import Port, Symbol
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
    if not 1 <= n <= len(ports):
        msg = (
            f"{symbol.name}: edge {edge.name} cannot carry n={n} ports; "
            f"it declares {len(ports)}; ask for 1 to {len(ports)}"
        )
        raise InvalidValueError(msg)
    return ports


def stretch_to_ports(
    symbol: Symbol, axis: Axis, edge: Direction, n: int, *, grid: Grid = DEFAULT_GRID
) -> tuple[float, dict[str, float]]:
    """Return the `length` and `offsets` for `stretch` so that `edge` carries n ports on the pitch.

    The n ports are the first n declared on the edge, in order along the axis. The first keeps
    its coordinate and the rest follow at the grid's standard wire pitch (`wire_pitch`, in
    module units). The ends keep the margins the symbol declares: from the body's low side to
    the first port, and from the last declared port to its high side. The length is the span
    those give, never below the natural extent, so `stretch(symbol, axis, length, offsets,
    grid=grid)` is valid. Call `only_ports` first so the edge holds only the ports you wire.

    Raises:
        InvalidValueError: If the symbol has no stretch on the axis, `edge` is not parallel to
            the axis, or n is below 1 or above the ports declared on the edge; the message names
            the symbol, the edge, n and the declared count.
    """
    ports = _edge_ports(symbol, axis, edge, n)
    pitch = from_divisions(grid, grid.wire_pitch)
    box = body_box(symbol)
    low, high = (box.min.x, box.max.x) if axis == "x" else (box.min.y, box.max.y)
    first, last = _along(ports[0], axis), _along(ports[-1], axis)
    length = max(high - low, (first - low) + (n - 1) * pitch + (high - last))
    return length, {p.id: first + i * pitch for i, p in enumerate(ports[:n])}
