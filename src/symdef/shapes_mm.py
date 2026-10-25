"""Bare shapes in millimetres: a rectangle, a box outline, a line and a group (D117, D125)."""

from xml.sax.saxutils import quoteattr

from symdef.errors import InvalidValueError, UnknownNameError
from symdef.geometry import Weight
from symdef.model import Library
from symdef.svg import _num, check_colour

type Box4 = tuple[float, float, float, float]
type Pt = tuple[float, float]


def _check_box(name: str, box: Box4) -> None:
    """Raise `InvalidValueError` for a box with a negative width or height."""
    if box[2] < 0 or box[3] < 0:
        msg = f"{name}: box size {box[2]} x {box[3]} must not be negative; pass a positive size"
        raise InvalidValueError(msg)


def _width(library: Library, weight: Weight) -> str:
    """Return the stroke width of `weight` in mm from `library.lines`; a missing one raises."""
    if weight not in library.lines:
        have = ", ".join(w.name for w in library.lines) or "none"
        msg = (
            f"no width for {weight.name} in library {library.standard!r}; it has {have}; "
            "pass a library with it in [lines]"
        )
        raise UnknownNameError(msg)
    return _num(library.lines[weight])


def _dash(library: Library, dash: str | None) -> str:
    """Return the dash attribute for a `library.dash` key, or nothing for `None`."""
    if dash is None:
        return ""
    if dash not in library.dash:
        have = ", ".join(sorted(library.dash)) or "none"
        msg = (
            f"no dash pattern {dash!r} in library {library.standard!r}; it has {have}; "
            "pass a library with that [dash] key"
        )
        raise UnknownNameError(msg)
    return f' stroke-dasharray="{" ".join(_num(n) for n in library.dash[dash])}"'


def _stroke(  # noqa: PLR0913 - the closing attributes of every shape are these things
    library: Library,
    *,
    weight: Weight,
    stroke: str,
    dash: str | None,
    classes: str,
    fill: str | None = None,
) -> tuple[str, str]:
    """Return the leading `class` and the closing stroke attributes of a shape; one home."""
    check_colour("stroke", stroke)
    check_colour("fill", fill)
    head = f" class={quoteattr(classes)}" if classes else ""
    paint = "" if fill is None else f' fill="{fill}"'
    tail = f'{paint} stroke="{stroke}" stroke-width="{_width(library, weight)}"'
    return head, tail + _dash(library, dash)


def rect_mm(  # noqa: PLR0913 - one rectangle is these things
    box: Box4,
    *,
    library: Library,
    weight: Weight,
    stroke: str,
    fill: str,
    dash: str | None = None,
    classes: str = "",
) -> str:
    """Return one SVG `<rect>` over `box` (x, y, width, height) in mm.

    `stroke` and `fill` are written as given, each `#rgb`, `#rrggbb` or a colour name. The stroke
    width is `library.lines[weight]`; `dash` is a key of `library.dash` or `None` for a solid
    line; `classes` is the element's `class`, left out when empty. Raises `InvalidValueError`
    for a negative width or height or a bad colour, and `UnknownNameError` for a `weight` or a
    `dash` the library lacks.
    """
    _check_box("rect_mm", box)
    x, y, width, height = box
    head, tail = _stroke(
        library, weight=weight, stroke=stroke, dash=dash, classes=classes, fill=fill
    )
    geometry = f'x="{_num(x)}" y="{_num(y)}" width="{_num(width)}" height="{_num(height)}"'
    return f"<rect{head} {geometry}{tail}/>"


def line_mm(  # noqa: PLR0913 - one line is these things
    a: Pt,
    b: Pt,
    *,
    library: Library,
    weight: Weight,
    stroke: str,
    dash: str | None = None,
    classes: str = "",
) -> str:
    """Return one SVG `<line>` from `a` to `b` in mm, written as `rect_mm` writes its stroke.

    Raises `InvalidValueError` for a bad colour, and `UnknownNameError` for a `weight` or a
    `dash` the library lacks.
    """
    head, tail = _stroke(library, weight=weight, stroke=stroke, dash=dash, classes=classes)
    geometry = f'x1="{_num(a[0])}" y1="{_num(a[1])}" x2="{_num(b[0])}" y2="{_num(b[1])}"'
    return f"<line{head} {geometry}{tail}/>"


def outline_mm(  # noqa: PLR0913 - one outline is these things
    box: Box4,
    *,
    library: Library,
    weight: Weight,
    stroke: str,
    dash: str | None = None,
    classes: str = "",
) -> str:
    """Return the unfilled outline of `box` (x, y, width, height) in mm.

    Solid, it is one `<rect>` with `fill="none"`. Dashed, it is four `<line>`s drawn left to right
    and top down: top, bottom, left, right. Dashes then start at the same corner on facing edges,
    so they stay in phase. Raises as `rect_mm` does.
    """
    _check_box("outline_mm", box)
    if dash is None:
        return rect_mm(
            box, library=library, weight=weight, stroke=stroke, fill="none", classes=classes
        )
    x, y, width, height = box
    right, bottom = x + width, y + height
    edges = (((x, y), (right, y)), ((x, bottom), (right, bottom)))
    edges += (((x, y), (x, bottom)), ((right, y), (right, bottom)))
    return "".join(
        line_mm(a, b, library=library, weight=weight, stroke=stroke, dash=dash, classes=classes)
        for a, b in edges
    )


def group_mm(body: str, at: Pt, *, classes: str = "") -> str:
    """Return `body` inside one `<g>` moved to `at` (x, y) in mm by `translate`.

    `classes` is the group's `class`, written first and left out when empty. `body` is written
    as given, so a fragment already in mm keeps its numbers; `at` has at most four decimals.
    """
    head = f" class={quoteattr(classes)}" if classes else ""
    return f'<g{head} transform="translate({_num(at[0])} {_num(at[1])})">{body}</g>'
