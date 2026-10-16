"""Wires: one open polyline drawn in a standard's named wire style."""

from collections.abc import Sequence

from symdef.errors import InvalidValueError, UnknownNameError
from symdef.geometry import Fill, Point, Polyline
from symdef.model import Library, Reference, Status, Symbol, SymbolKind

_MIN_POINTS = 2


def wire(
    library: Library,
    style_id: str,
    points: Sequence[Point] | Sequence[tuple[float, float]],
) -> Symbol:
    """Return an element symbol that draws one open polyline through `points` in a wire style.

    Args:
        library: The library whose `wires` name the style.
        style_id: The id of one of its wire styles.
        points: The corners in module units, as `Point`s or (x, y) pairs.

    Returns:
        An unverified element symbol with one open polyline and no ports, slots, nodes or paths.

    Raises:
        UnknownNameError: If the library has no wire style with this id.
        InvalidValueError: If fewer than two points are given.
    """
    styles = {w.id: w for w in library.wires}
    if style_id not in styles:
        known = ", ".join(sorted(styles)) or "none"
        msg = f"no wire style {style_id!r} in {library.standard}; its styles are {known}; use one"
        raise UnknownNameError(msg)
    if len(points) < _MIN_POINTS:
        msg = f"a wire needs at least {_MIN_POINTS} points, got {len(points)}"
        raise InvalidValueError(msg)
    style = styles[style_id]
    corners = tuple(p if isinstance(p, Point) else Point(*p) for p in points)
    line = Polyline(corners, closed=False, fill=Fill.NONE, weight=style.weight, style=style.style)
    return Symbol(
        name=f"wire {style_id}",
        kind=SymbolKind.ELEMENT,
        status=Status.UNVERIFIED,
        reference=Reference(library.standard, f"wire.{style_id}"),
        elements=(line,),
    )
