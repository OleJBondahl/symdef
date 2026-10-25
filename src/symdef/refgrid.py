"""The reference grid of a page frame: which cell holds a point (D129)."""

from collections.abc import Sequence

from symdef.errors import InvalidValueError, ReferenceCellError
from symdef.gridtypes import GridPoint


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
