"""Wires: one polyline, open or closed, drawn in a standard's named wire style."""

from collections.abc import Sequence

from symdef.errors import InvalidValueError, UnknownNameError
from symdef.geometry import Fill, Point, Polyline
from symdef.model import Library, Reference, Status, Symbol, SymbolKind

_MIN_POINTS = 2
_MIN_CLOSED = 3


def wire(
    library: Library,
    style_id: str,
    points: Sequence[Point] | Sequence[tuple[float, float]],
    *,
    closed: bool = False,
) -> Symbol:
    """Return an element symbol that draws one polyline through `points` in a wire style.

    Args:
        library: The library whose `wires` name the style.
        style_id: The id of one of its wire styles.
        points: The corners in module units, as `Point`s or (x, y) pairs.
        closed: True to join the last corner back to the first, so the closing corner is joined
            like the others instead of ending in two butt caps (D95).

    Returns:
        An unverified element symbol with one polyline, open unless `closed`, and no ports,
        slots, nodes or paths.

    Raises:
        UnknownNameError: If the library has no wire style with this id.
        InvalidValueError: If fewer than two points are given, or fewer than three when `closed`.
    """
    styles = {w.id: w for w in library.wires}
    if style_id not in styles:
        known = ", ".join(sorted(styles)) or "none"
        msg = f"no wire style {style_id!r} in {library.standard}; its styles are {known}; use one"
        raise UnknownNameError(msg)
    least = _MIN_CLOSED if closed else _MIN_POINTS
    if len(points) < least:
        msg = (
            f"a {'closed ' if closed else ''}wire needs at least {least} points, got {len(points)}"
        )
        raise InvalidValueError(msg)
    style = styles[style_id]
    corners = tuple(p if isinstance(p, Point) else Point(*p) for p in points)
    line = Polyline(corners, closed=closed, fill=Fill.NONE, weight=style.weight, style=style.style)
    return Symbol(
        name=f"wire {style_id}",
        kind=SymbolKind.ELEMENT,
        status=Status.UNVERIFIED,
        reference=Reference(library.standard, f"wire.{style_id}"),
        elements=(line,),
    )
