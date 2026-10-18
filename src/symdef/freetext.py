"""Free text: one `<text>` tag in millimetres, and where a box's corner puts its baseline (D100)."""

from typing import Literal
from xml.sax.saxutils import quoteattr

from symdef.errors import InvalidValueError
from symdef.font import FontMetrics, cap_height
from symdef.geometry import Box, Point, Weight
from symdef.slottext import Anchor, TextPlacement
from symdef.svg import _num, check_colour, slot_text_tag

type Corner = Literal["NW", "NE", "SW", "SE"]

_ANCHOR: dict[str, Anchor] = {"W": "start", "E": "end"}


def text_tag(  # noqa: PLR0913 - one free text tag is these things
    content: str,
    point: Point,
    height_mm: float,
    *,
    anchor: Anchor,
    font_family: str,
    turn: bool = False,
    weight: Weight = Weight.NORMAL,
    tint: str | None = None,
    muted: str | None = None,
) -> str:
    """Return one SVG `<text>` fragment in millimetres, anchored at the baseline point `point`.

    `height_mm` is the font size. `anchor` says which end of the text sits on `point`. `turn`
    rotates the text -90 degrees about `point`. `Weight.THICK` is `font-weight="bold"`. The fill
    is `muted` when given, else `tint`, else black; each is `#rgb`, `#rrggbb` or a colour name.
    `font_family` is escaped here for the attribute. Raises `InvalidValueError` for a bad colour.
    """
    check_colour("tint", tint)
    check_colour("muted", muted)
    return slot_text_tag(
        (_num(point.x), _num(point.y)),
        _num(height_mm),
        anchor=anchor,
        fill=muted or tint or "#000",
        family=quoteattr(font_family),
        content=content,
        turn=turn,
        bold=weight is Weight.THICK,
    )


def corner_text(box: Box, corner: Corner, height: float, font: FontMetrics | None) -> TextPlacement:
    """Return where a one-line text of `height` sits at a corner of `box`, as `slot_text` does.

    The text hangs inside the box on that corner: `W` corners start at the box's west edge and `E`
    corners end at its east edge; `N` corners put the capitals' top on the north edge, `S` corners
    put the baseline on the south edge. The result is upright, in the box's own unit. Raises
    `InvalidValueError` for a corner that is not one of the four.
    """
    if corner not in ("NW", "NE", "SW", "SE"):
        msg = f"corner_text: corner {corner!r} is not valid; use 'NW', 'NE', 'SW' or 'SE'"
        raise InvalidValueError(msg)
    north, west = corner[0] == "N", corner[1] == "W"
    x = box.min.x if west else box.max.x
    y = box.min.y + cap_height(font, height) if north else box.max.y
    return TextPlacement(Point(x, y), _ANCHOR[corner[1]], turned=False)
