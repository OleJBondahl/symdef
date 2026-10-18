"""Wires: one polyline, open or closed, drawn in a standard's named wire style."""

import itertools
from collections.abc import Sequence

from symdef.errors import InvalidValueError, UnknownNameError
from symdef.geometry import Fill, Point, Polyline
from symdef.model import Library, Reference, Status, Symbol, SymbolKind
from symdef.units import from_divisions

_MIN_POINTS = 2
_MIN_CLOSED = 3


def wire(  # noqa: PLR0913 - the signature is fixed by designer Ruling 62
    library: Library,
    style_id: str,
    points: Sequence[Point] | Sequence[tuple[float, float]],
    *,
    closed: bool = False,
    lanes: int = 1,
    pitch: float | None = None,
) -> Symbol:
    """Return an element symbol that draws `lanes` parallel polylines through `points`.

    Args:
        library: The library whose `wires` name the style.
        style_id: The id of one of its wire styles.
        points: The corners in module units, as `Point`s or (x, y) pairs.
        closed: True to join the last corner back to the first, so the closing corner is joined
            like the others instead of ending in two butt caps (D95).
        lanes: How many parallel polylines to draw. Lane 0 lies on `points`; lane k is moved
            k * `pitch` towards +y on a horizontal run and +x on a vertical run, mitred at the
            corners (D99).
        pitch: The distance between lanes in module units; default `library.grid.wire_pitch`.

    Returns:
        An unverified element symbol with one polyline per lane in lane order, open unless
        `closed`, and no ports, slots, nodes or paths.

    Raises:
        UnknownNameError: If the library has no wire style with this id.
        InvalidValueError: If fewer than two points are given, or fewer than three when `closed`;
            if `lanes` is below 1 or `pitch` is not above 0; if `lanes` is above 1 and the wire
            is `closed`, or a run is not horizontal or vertical or has no length.
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
    step = _lane_step(library, lanes, pitch, closed=closed)
    lines = tuple(
        Polyline(
            _lane(corners, k * step),
            closed=closed,
            fill=Fill.NONE,
            weight=style.weight,
            style=style.style,
        )
        for k in range(lanes)
    )
    return Symbol(
        name=f"wire {style_id}",
        kind=SymbolKind.ELEMENT,
        status=Status.UNVERIFIED,
        reference=Reference(library.standard, f"wire.{style_id}"),
        elements=lines,
    )


def _lane_step(library: Library, lanes: int, pitch: float | None, *, closed: bool) -> float:
    """Return the lane distance in module units, or raise for a value `wire` cannot draw."""
    if lanes < 1:
        msg = f"lanes must be at least 1, got {lanes}; use lanes=1 for a single wire"
        raise InvalidValueError(msg)
    if closed and lanes > 1:
        msg = f"a closed wire has one lane, got lanes={lanes}; draw an open wire or use lanes=1"
        raise InvalidValueError(msg)
    if pitch is None:
        return from_divisions(library.grid, library.grid.wire_pitch)
    if pitch <= 0:
        msg = f"pitch must be above 0, got {pitch}; omit it for the grid's wire pitch"
        raise InvalidValueError(msg)
    return pitch


def _lane(corners: tuple[Point, ...], distance: float) -> tuple[Point, ...]:
    """Return the corners moved `distance` towards +y on horizontal runs and +x on vertical ones."""
    if distance == 0:
        return corners
    runs = [_is_horizontal(a, b) for a, b in itertools.pairwise(corners)]
    moved = []
    for i, p in enumerate(corners):
        near = runs[max(i - 1, 0) : i + 1]
        dx = distance if False in near else 0.0
        dy = distance if True in near else 0.0
        moved.append(Point(p.x + dx, p.y + dy))
    return tuple(moved)


def _is_horizontal(a: Point, b: Point) -> bool:
    """Return True for a horizontal run and False for a vertical one; raise for any other."""
    if (a.y == b.y) == (a.x == b.x):
        msg = f"a lane run from {a} to {b} must be horizontal or vertical and have a length"
        raise InvalidValueError(msg)
    return a.y == b.y
