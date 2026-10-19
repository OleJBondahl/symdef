"""Where `table` puts its rows along the axis, and how a head lines up with them."""

from collections.abc import Sequence
from math import fsum
from typing import Literal

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.geometry import Box
from symdef.model import Symbol
from symdef.stretch import Axis

HeadAlign = Literal["start", "center", "end"]
_ALIGNS = ("start", "center", "end")
_NOISE = 1e-9


def low_of(box: Box, axis: Axis) -> float:
    """Return the box's low edge on the axis."""
    return box.min.x if axis == "x" else box.min.y


def extent_of(box: Box, axis: Axis) -> float:
    """Return the box's extent along the axis."""
    return box.width if axis == "x" else box.height


def _checked_gaps(gaps: Sequence[float] | None, n: int) -> tuple[float, ...]:
    """Return the n - 1 gaps after rows 1 to n - 1, zeros when none are given."""
    if gaps is None:
        return (0.0,) * (n - 1)
    if len(gaps) != n - 1:
        msg = f"gaps needs {n - 1} numbers, one after each row but the last, got {len(gaps)}"
        raise InvalidValueError(msg)
    for i, gap in enumerate(gaps, start=1):
        if not gap >= 0:
            msg = f"the gap after row {i} is {gap!r}; use 0 or more"
            raise InvalidValueError(msg)
    return tuple(gaps)


def _checked_positions(
    positions: Sequence[float], extents: Sequence[float], n: int
) -> tuple[float, ...]:
    """Return the positions, each row clear of the one before."""
    if len(positions) != n:
        msg = f"positions needs {n} numbers, one for each row, got {len(positions)}"
        raise InvalidValueError(msg)
    for k in range(1, n):
        end = positions[k - 1] + extents[k - 1]
        if positions[k] < end - _NOISE:
            msg = (
                f"row {k + 1} starts at {positions[k]!r}, inside row {k}, which ends at {end!r}; "
                "positions must not overlap"
            )
            raise InvalidValueError(msg)
    return tuple(positions)


def row_offsets(
    rows: Sequence[Symbol],
    axis: Axis,
    gaps: Sequence[float] | None,
    positions: Sequence[float] | None,
) -> tuple[float, ...]:
    """Return how far each row moves along the axis; row 1 stays unless `positions` moves it."""
    if gaps is not None and positions is not None:
        msg = "gaps and positions are mutually exclusive; pass one of them"
        raise InvalidValueError(msg)
    boxes = tuple(body_box(r) for r in rows)
    extents = tuple(extent_of(b, axis) for b in boxes)
    lows = tuple(low_of(b, axis) for b in boxes)
    if positions is not None:
        placed = _checked_positions(positions, extents, len(rows))
        return tuple(p - low for p, low in zip(placed, lows, strict=True))
    steps = tuple(e + g for e, g in zip(extents, _checked_gaps(gaps, len(rows)), strict=False))
    return tuple(fsum(steps[: k - 1]) + (lows[0] - lows[k - 1]) for k in range(1, len(rows) + 1))


def span_of(rows: Sequence[Symbol], offsets: Sequence[float], axis: Axis) -> tuple[float, float]:
    """Return the low edge and extent of the moved rows together."""
    boxes = tuple(body_box(r) for r in rows)
    lows = [low_of(b, axis) + o for b, o in zip(boxes, offsets, strict=True)]
    highs = [low + extent_of(b, axis) for low, b in zip(lows, boxes, strict=True)]
    return min(lows), max(highs) - min(lows)


def check_align(align: str) -> None:
    """Raise unless `align` is "start", "center" or "end"."""
    if align not in _ALIGNS:
        msg = f"head_align must be one of 'start', 'center' or 'end', got {align!r}"
        raise InvalidValueError(msg)


def align_shift(
    align: str, head_box: Box, low: float, extent: float, axis: Axis
) -> tuple[float, float]:
    """Return the shifts of the head and of the rows that line the narrower up in the wider.

    The head moves when it is no wider than the rows, otherwise the rows move.
    """
    check_align(align)
    head_low, head_extent = low_of(head_box, axis), extent_of(head_box, axis)
    narrow_is_head = head_extent <= extent
    wide_low, wide_extent = (low, extent) if narrow_is_head else (head_low, head_extent)
    narrow_low, narrow_extent = (head_low, head_extent) if narrow_is_head else (low, extent)
    room = wide_extent - narrow_extent
    where = {"start": 0.0, "center": room / 2, "end": room}[align]
    shift = wide_low + where - narrow_low
    return (shift, 0.0) if narrow_is_head else (0.0, shift)


def rows_length(rows: Sequence[Symbol], axis: Axis, gaps: Sequence[float] | None) -> float:
    """Return the extents of all rows and the gaps between them added up."""
    extents = [extent_of(body_box(r), axis) for r in rows]
    return fsum(extents) + fsum(gaps or ())
