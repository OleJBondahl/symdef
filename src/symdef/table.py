"""`table`: n rows along an axis, ports and slots prefixed, an optional head placed as authored."""

from dataclasses import replace

from symdef.boxes import body_box
from symdef.model import Slot, Symbol, nodes_of
from symdef.orient import translate
from symdef.repeat import MAX_REPEAT, pole_elements, pole_parts
from symdef.stretch import Axis, stretch

_MARKING = "marking."


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


def table(row: Symbol, n: int, axis: Axis, head: Symbol | None = None) -> Symbol:
    """Return `n` rows placed one after another along an axis, as an ordinary symbol.

    Row k (from 1) is the row translated by `k - 1` times its body extent along the axis. Ports,
    paths, nodes and bound leads are prefixed `<k>.`, as `repeat` does. Every slot of every row is
    kept: `marking.<port>` becomes `marking.<k>.<port>`, any other `<id>` becomes `<k>.<id>`. Row
    1's anchors become the result's anchors. The head keeps its own ids and comes first; if it has
    a stretch on the axis, it is stretched to span all `n` rows. The head is placed as authored,
    in the row's frame: author it before the first row on the axis or, with a stretch on the axis,
    spanning the rows. The result has no stretch and the row's `pole_pitch`.

    Args:
        row: A symbol in base orientation.
        n: The row count, from 1 to `MAX_REPEAT`.
        axis: "x" or "y".
        head: A symbol placed once before the rows, or None.

    Returns:
        The table, carrying the row's name, kind, status, reference and lint allowances.

    Raises:
        ValueError: If `n` is outside 1 to `MAX_REPEAT`, or the head's stretch cannot span `n` rows.
    """
    if not 1 <= n <= MAX_REPEAT:
        msg = f"the row count must be between 1 and {MAX_REPEAT}, got {n}"
        raise ValueError(msg)
    box = body_box(row)
    step = box.width if axis == "x" else box.height
    rows = tuple(translate(row, *_offset(axis, (k - 1) * step)) for k in range(1, n + 1))
    if head is not None and any(s.axis == axis for s in head.stretch):
        head = stretch(head, axis, n * step)
    if head is None:
        head_elements, head_ports, head_nodes, head_paths, head_slots = ((),) * 5
    else:
        head_elements, head_ports, head_nodes = head.elements, head.ports, nodes_of(head)
        head_paths, head_slots = head.paths, head.slots
    parts = tuple(pole_parts(r, k) for k, r in enumerate(rows, start=1))
    return replace(
        row,
        elements=head_elements
        + tuple(e for k, r in enumerate(rows, start=1) for e in pole_elements(r.elements, k)),
        ports=head_ports + tuple(p for ports, _, _ in parts for p in ports),
        nodes=head_nodes + tuple(node for _, nodes, _ in parts for node in nodes),
        paths=head_paths + tuple(path for _, _, paths in parts for path in paths),
        anchors=rows[0].anchors,
        slots=head_slots
        + tuple(s for k, r in enumerate(rows, start=1) for s in _row_slots(r.slots, k)),
        stretch=(),
    )
