"""`table`: n rows along an axis, ports and slots prefixed, an optional head placed as authored."""

from collections.abc import Sequence
from dataclasses import replace

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.geometry import Element, Line, Polyline
from symdef.model import Slot, Symbol, nodes_of
from symdef.orient import translate
from symdef.repeat import MAX_REPEAT, ROW_PORT_FORMAT, declared_union, pole_elements, pole_parts
from symdef.stretch import Axis, stretch
from symdef.table_rows import (
    HeadAlign,
    align_shift,
    check_align,
    extent_of,
    row_offsets,
    rows_length,
    span_of,
)
from symdef.units import Grid

_MARKING = "marking."


def _row_elements(row: Symbol, k: int, n: int) -> tuple[Element, ...]:
    """Return row `k` of `n`'s elements; a `between` element is left out of the last row."""
    elements = pole_elements(row.elements, k, ROW_PORT_FORMAT)
    if k < n:
        return elements
    return tuple(e for e in elements if not (isinstance(e, Line | Polyline) and e.between))


def _row_slots(slots: tuple[Slot, ...], k: int) -> tuple[Slot, ...]:
    """Return row `k`'s slots, all kept: `marking.<port>` becomes `marking.<k>.<port>`."""
    return tuple(
        replace(s, id=f"{_MARKING}{k}.{s.id.removeprefix(_MARKING)}")
        if s.id.startswith(_MARKING)
        else replace(s, id=f"{k}.{s.id}")
        for s in slots
    )


def _offset(axis: Axis, distance: float) -> tuple[float, float]:
    """Return the shift of `distance` along the axis."""
    return (distance, 0) if axis == "x" else (0, distance)


def _given(row: Symbol | Sequence[Symbol], n: int) -> tuple[Symbol, ...]:
    """Return the `n` rows: the one symbol `n` times, or the sequence, which must hold `n`."""
    given = (row,) * n if isinstance(row, Symbol) else tuple(row)
    if len(given) != n:
        msg = f"table got {len(given)} rows but n is {n}; pass n equal to the number of rows"
        raise InvalidValueError(msg)
    return given


def _spanned(
    head: Symbol | None, axis: Axis, span: float, grid: Grid | None, head_align: str | None
) -> Symbol | None:
    """Return the head stretched to span the rows; a wider head is left alone when aligned."""
    if head is None or not any(s.axis == axis for s in head.stretch):
        return head
    if head_align is not None and extent_of(body_box(head), axis) > span:
        return head
    return stretch(head, axis, span, grid=grid)


def _placed(
    rows: Sequence[Symbol],
    axis: Axis,
    head: Symbol | None,
    grid: Grid | None,
    plan: tuple[Sequence[float] | None, Sequence[float] | None, str | None],
) -> tuple[tuple[Symbol, ...], Symbol | None]:
    """Return the rows moved to their places and the head stretched and lined up with them."""
    gaps, positions, head_align = plan
    if head_align is not None:
        check_align(head_align)
    offsets = row_offsets(rows, axis, gaps, positions)
    low, span = span_of(rows, offsets, axis)
    if positions is None:
        span = rows_length(rows, axis, gaps)
    head = _spanned(head, axis, span, grid, head_align)
    head_shift = row_shift = 0.0
    if head is not None and head_align is not None:
        head_shift, row_shift = align_shift(head_align, body_box(head), low, span, axis)
    if head is not None:
        head = translate(head, *_offset(axis, head_shift))
    moved = tuple(
        translate(r, *_offset(axis, o + row_shift)) for r, o in zip(rows, offsets, strict=True)
    )
    return moved, head


def table(  # noqa: PLR0913 - the ruled signature: row, n, axis, head and the keyword options
    row: Symbol | Sequence[Symbol],
    n: int,
    axis: Axis,
    head: Symbol | None = None,
    *,
    grid: Grid | None = None,
    gaps: Sequence[float] | None = None,
    positions: Sequence[float] | None = None,
    head_align: HeadAlign | None = None,
) -> Symbol:
    """Return `n` rows placed one after another along an axis, as an ordinary symbol.

    Row k (from 1) is the row translated by `k - 1` times its body extent along the axis. `row` may
    be a sequence of `n` unlike symbols: each is placed so its body low edge on the axis meets a
    cursor that starts at row 1's low edge and advances by that row's own extent. Ports, paths,
    nodes and bound leads are prefixed `<k>.`, as `repeat` does. Every slot of every row is
    kept: `marking.<port>` becomes `marking.<k>.<port>`, any other `<id>` becomes `<k>.<id>`. Row
    1's anchors become the result's anchors. The head keeps its own ids and comes first; if it has
    a stretch on the axis, it is stretched to span all `n` rows. The head is placed as authored,
    in the row's frame: author it before the first row on the axis or, with a stretch on the axis,
    spanning the rows. A `between` element is drawn in rows 1 to n-1 and left out of row n; a
    single row draws none, and the head is unaffected. The result has no stretch and the first
    row's `pole_pitch`.

    `gaps` adds space after rows 1 to n-1; `positions` instead names the coordinate of each row's
    low edge, rows never overlapping. `head_align` ("start", "center" or "end") lines the narrower
    of the head and the rows up in the wider along the axis; a head already wider than the rows is
    then not stretched.

    Args:
        row: A symbol in base orientation, or a sequence of `n` of them.
        n: The row count, from 1 to `MAX_REPEAT`.
        axis: "x" or "y".
        head: A symbol placed once before the rows, or None.
        grid: The library's grid, passed to the head's `stretch`, or None.
        gaps: `n - 1` numbers of at least 0, the extra space after each row but the last.
        positions: `n` coordinates for the rows' low edges, or None; not with `gaps`.
        head_align: How the head lines up with the rows along the axis, or None for as authored.

    Returns:
        The table, carrying the first row's name, kind, status, reference and lint allowances.

    Raises:
        InvalidValueError: If `n` is outside 1 to `MAX_REPEAT` or differs from the number of rows
            given, `gaps` or `positions` has the wrong length, a gap is below zero, rows overlap,
            both are given, `head_align` is not one of the three, or the head's stretch cannot
            span the rows.
    """
    if not 1 <= n <= MAX_REPEAT:
        msg = f"the row count must be between 1 and {MAX_REPEAT}, got {n}"
        raise InvalidValueError(msg)
    given = _given(row, n)
    rows, head = _placed(given, axis, head, grid, (gaps, positions, head_align))
    first = given[0]
    if head is None:
        head_elements, head_ports, head_nodes, head_paths, head_slots = ((),) * 5
    else:
        head_elements, head_ports, head_nodes = head.elements, head.ports, nodes_of(head)
        head_paths, head_slots = head.paths, head.slots
    parts = tuple(pole_parts(r, k, ROW_PORT_FORMAT) for k, r in enumerate(rows, start=1))
    return replace(
        first,
        elements=head_elements
        + tuple(e for k, r in enumerate(rows, start=1) for e in _row_elements(r, k, n)),
        ports=head_ports + tuple(p for ports, _, _ in parts for p in ports),
        nodes=head_nodes + tuple(node for _, nodes, _ in parts for node in nodes),
        paths=head_paths + tuple(path for _, _, paths in parts for path in paths),
        anchors=rows[0].anchors,
        slots=head_slots
        + tuple(s for k, r in enumerate(rows, start=1) for s in _row_slots(r.slots, k)),
        stretch=(),
        body=declared_union((*(() if head is None else (head.body,)), *(r.body for r in rows))),
        keepout=declared_union(
            (*(() if head is None else (head.keepout,)), *(r.keepout for r in rows))
        ),
    )
