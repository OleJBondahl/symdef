"""The reference grid of a page frame: which cell holds a point (D129)."""

from collections.abc import Sequence
from typing import Literal

from symdef.errors import InvalidValueError, ReferenceCellError
from symdef.gridtypes import GridPoint

LabelKind = Literal["letters", "numbers"]
RowOrder = Literal["top_down", "bottom_up"]
_LETTERS = 26


def _index(label_count: int, extent: int, at: int) -> int:
    """Return the 0-based cell of `at` on one axis, the far edge counting in the last cell."""
    return min(at * label_count // extent, label_count - 1)


def reference_cell(
    columns: Sequence[str],
    rows: Sequence[str],
    width: int,
    height: int,
    point: GridPoint,
) -> tuple[str, str]:
    """Return the (column label, row label) of the cell holding `point` in a frame's reference grid.

    The grid divides the content box, `width` by `height` grid divisions with its origin at the
    min corner, evenly into one cell per label: `columns` left to right, `rows` top to bottom
    (the smallest y first). A point on a shared edge belongs to the cell on its max side, and
    a point on the far edge of the box to the last cell. The labels are the frame's own and
    are returned as given.

    Raises:
        InvalidValueError: `columns` or `rows` is empty, or `width` or `height` is not above zero.
        ReferenceCellError: `point` lies outside the box; no clamping.
    """
    if not columns or not rows:
        msg = "a reference grid needs at least one column label and one row label; give both"
        raise InvalidValueError(msg)
    if width < 1 or height < 1:
        msg = f"the reference grid box is {width} by {height} divisions; give both above zero"
        raise InvalidValueError(msg)
    if not (0 <= point.x <= width and 0 <= point.y <= height):
        msg = (
            f"point ({point.x}, {point.y}) lies outside the reference grid of "
            f"{len(columns)} columns "
            f"by {len(rows)} rows over {width} by {height} divisions; "
            f"give a point from (0, 0) to ({width}, {height})"
        )
        raise ReferenceCellError(msg)
    return columns[_index(len(columns), width, point.x)], rows[_index(len(rows), height, point.y)]


def _labels(axis: str, kind: str, count: int) -> tuple[str, ...]:
    """Return `count` labels of one axis in their own order: `A, B, ...` or `1, 2, ...`."""
    if count < 1:
        msg = f"a reference grid needs at least one {axis}; give {axis}s of 1 or more"
        raise InvalidValueError(msg)
    if kind == "numbers":
        return tuple(str(i + 1) for i in range(count))
    if kind != "letters":
        msg = f'the {axis} labels are "{kind}"; known: "letters", "numbers"'
        raise InvalidValueError(msg)
    if count > _LETTERS:
        msg = (
            f"{count} {axis}s do not fit the letters A to Z; give at most {_LETTERS} or use numbers"
        )
        raise InvalidValueError(msg)
    return tuple(chr(ord("A") + i) for i in range(count))


def reference_labels(
    columns: int,
    rows: int,
    *,
    column_kind: LabelKind = "letters",
    row_kind: LabelKind = "numbers",
    row_order: RowOrder = "top_down",
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the (column labels, row labels) of a frame of `columns` by `rows` cells.

    Columns run left to right and rows top to bottom, each labelled `letters` (A, B, ...; at
    most 26) or `numbers` (1, 2, ...). With `row_order="bottom_up"` the row labels count from
    the bottom, so the top row carries the highest. They fit `reference_cell`.

    Raises:
        InvalidValueError: A count is below 1, more than 26 labels are letters, or a kind or
            order is not one of the values named in the message.
    """
    if row_order not in ("top_down", "bottom_up"):
        msg = f'the row order is "{row_order}"; known: "top_down", "bottom_up"'
        raise InvalidValueError(msg)
    row_labels = _labels("row", row_kind, rows)
    if row_order == "bottom_up":
        row_labels = row_labels[::-1]
    return _labels("column", column_kind, columns), row_labels


def reference_origin(
    columns: Sequence[str],
    rows: Sequence[str],
    width: int,
    height: int,
    column: str,
    row: str,
) -> GridPoint:
    """Return the min corner of the cell `column`, `row` of a reference grid, the inverse of `reference_cell`.

    The grid is the one `reference_cell` takes. The origin is the first whole division that
    `reference_cell` places in the cell, so `reference_cell(..., reference_origin(..., c, r))`
    gives `(c, r)` for every cell. A cell narrower than one division has no such point.

    Raises:
        InvalidValueError: A label is not in `columns` or `rows` (the message lists the known
            ones), the grid is unusable as in `reference_cell`, or a label count exceeds its
            divisions.
    """
    if not columns or not rows:
        msg = "a reference grid needs at least one column label and one row label; give both"
        raise InvalidValueError(msg)
    if width < 1 or height < 1:
        msg = f"the reference grid box is {width} by {height} divisions; give both above zero"
        raise InvalidValueError(msg)
    if len(columns) > width or len(rows) > height:
        msg = (
            f"{len(columns)} columns by {len(rows)} rows do not fit {width} by {height} "
            "divisions; give at least one division per cell"
        )
        raise InvalidValueError(msg)
    return GridPoint(_origin("column", columns, width, column), _origin("row", rows, height, row))


def _origin(axis: str, labels: Sequence[str], extent: int, label: str) -> int:
    """Return the first division of the cell `label` on one axis; an unknown label raises."""
    if label not in labels:
        msg = f'no {axis} "{label}" in the reference grid; known: {", ".join(labels)}'
        raise InvalidValueError(msg)
    return -(-labels.index(label) * extent // len(labels))
