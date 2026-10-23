"""SVG fragment in millimetres: the exact-size output, with no scale transform."""

from collections.abc import Mapping, Sequence
from typing import NamedTuple
from xml.sax.saxutils import quoteattr

from symdef.errors import InvalidValueError, UnknownNameError
from symdef.geometry import (
    Arc,
    Circle,
    Element,
    Fill,
    Line,
    Point,
    Polyline,
    Style,
    Text,
    Weight,
    arc_point,
    arc_sweep,
)
from symdef.model import Library, Symbol
from symdef.slottext import stack_shifts
from symdef.svg import (
    _FULL_TURN,
    _HALF_TURN,
    _content,
    _num,
    _slots_by_id,
    check_colour,
    check_texts,
    check_tint,
    group_open,
    slot_align,
    slot_text_tag,
)


class _Mm(NamedTuple):
    """The caller's physical sizes, as `to_fragment_mm` receives them."""

    module: float
    weights: Mapping[Weight, float]
    dash: tuple[float, ...] | None
    dash_dot: tuple[float, ...] | None
    family: str
    font: float
    cap_ratio: float
    muted: str | None

    def xy(self, p: Point) -> tuple[str, str]:
        """Return a point as two millimetre numbers."""
        return _num(p.x * self.module), _num(p.y * self.module)

    def width(self, weight: Weight) -> str:
        """Return the stroke width of a weight in mm; a weight the caller left out raises."""
        if weight not in self.weights:
            have = ", ".join(w.name for w in self.weights)
            msg = (
                f"no width for {weight.name}; it has {have or 'none'}; "
                "add it to weights_mm or pass a library with it in [lines]"
            )
            raise UnknownNameError(msg)
        return _num(self.weights[weight])

    def stroke(
        self,
        weight: Weight,
        fill: Fill = Fill.NONE,
        style: Style = Style.SOLID,
        tint: str | None = None,
    ) -> str:
        """Return the closing attributes of a stroked shape, widths and dashes in mm."""
        dashed = self.dashes(style)
        if self.muted is not None and fill is not Fill.NONE:
            solid = f' fill="{self.muted}"'
        elif fill is Fill.SOLID:
            solid = ' fill="#000"'
        elif fill is Fill.TINT:
            colour = "none" if tint is None else tint
            solid = f' fill="{colour}"'
        else:
            solid = ""
        width = self.width(weight)
        return f'stroke-width="{width}"{dashed}{solid}/>'

    def dashes(self, style: Style) -> str:
        """Return the dash attribute of a line style, or nothing for a solid line.

        A muted symbol has one pattern for every style: a dash and a gap of the normal width.
        """
        if self.muted is not None:
            normal = self.width(Weight.NORMAL)
            return f' stroke-dasharray="{normal} {normal}"'
        if style is Style.DASH_DOT:
            if self.dash_dot is None:
                message = (
                    "dash_dot_mm is required to draw a dash_dot element; "
                    "pass it or a library with a dash_dot pattern in [dash]"
                )
                raise InvalidValueError(message)
            return f' stroke-dasharray="{" ".join(_num(n) for n in self.dash_dot)}"'
        if style is Style.DASHED:
            if self.dash is None:
                message = (
                    "no dash pattern for dashed; pass dash_mm or a library with dashed in [dash]"
                )
                raise UnknownNameError(message)
            return f' stroke-dasharray="{_num(self.dash[0])} {_num(self.dash[1])}"'
        return ""

    def moved(self, v: float, fraction: float) -> str:
        """Return a coordinate in module units as mm, moved on by a fraction of the cap height."""
        return _num(v * self.module + self.cap_ratio * self.font * fraction)

    def pair(self, p: Point) -> str:
        """Return a point as `x y`."""
        return " ".join(self.xy(p))


def _arc(mm: _Mm, arc: Arc) -> str:
    start = arc_point(arc, arc.start_deg)
    sweep = arc_sweep(arc)
    r = _num(arc.radius * mm.module)
    move = f"M {mm.pair(start)} A {r} {r} 0 "
    if sweep == _FULL_TURN:
        mid = arc_point(arc, arc.start_deg + _HALF_TURN)
        d = f"{move}0 1 {mm.pair(mid)} A {r} {r} 0 0 1 {mm.pair(start)}"
    else:
        large = 1 if sweep > _HALF_TURN else 0
        d = f"{move}{large} 1 {mm.pair(arc_point(arc, arc.end_deg))}"
    return f'<path d="{d}" {mm.stroke(arc.weight, style=arc.style)}'


def _text(mm: _Mm, text: Text) -> str:
    x = _num(text.position.x * mm.module)
    y = mm.moved(text.position.y, 0.5)
    return (
        f'<text x="{x}" y="{y}" font-size="{_num(mm.font)}" text-anchor="middle" '
        f'fill="{mm.muted or "#000"}" '
        f'stroke="none" font-family={quoteattr(mm.family)}>{_content(text.content)}</text>'
    )


def _slot_texts(mm: _Mm, symbol: Symbol, texts: Mapping[str, str] | None) -> list[str]:
    """Draw the caller's strings, one tag per slot in id order; the size is the caller's font."""
    if texts is None:
        return []
    tags = []
    for slot in _slots_by_id(symbol):
        if texts.get(slot.id):
            anchor, east, south = slot_align(slot)
            lines = texts[slot.id].split("\n")
            for line, shift in zip(lines, stack_shifts(slot, len(lines)), strict=True):
                across = (east + shift, south) if slot.turn else (east, south + shift)
                tag = slot_text_tag(
                    (
                        mm.moved(slot.position.x, across[0]),
                        mm.moved(slot.position.y, across[1]),
                    ),
                    _num(mm.font),
                    anchor=anchor,
                    fill=mm.muted or "#000",
                    family=quoteattr(mm.family),
                    content=line,
                    turn=slot.turn,
                )
                tags.append(tag)
    return tags


def _element(mm: _Mm, element: Element, tint: str | None) -> str:
    match element:
        case Line(start=s, end=e, weight=weight, style=style):
            (x1, y1), (x2, y2) = mm.xy(s), mm.xy(e)
            return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {mm.stroke(weight, style=style)}'
        case Polyline(points=points, closed=closed, fill=fill, weight=weight, style=style):
            tag = "polygon" if closed else "polyline"
            pts = " ".join(",".join(mm.xy(p)) for p in points)
            return f'<{tag} points="{pts}" {mm.stroke(weight, fill, style, tint)}'
        case Circle(center=c, radius=r, fill=fill, weight=weight):
            cx, cy = mm.xy(c)
            return (
                f'<circle cx="{cx}" cy="{cy}" r="{_num(r * mm.module)}" '
                f"{mm.stroke(weight, fill, tint=tint)}"
            )
        case Arc() as arc:
            return _arc(mm, arc)
        case Text() as text:
            return _text(mm, text)


def to_fragment_mm(  # noqa: PLR0913 - one physical size per keyword
    symbol: Symbol,
    *,
    module_mm: float,
    weights_mm: Mapping[Weight, float] | None = None,
    dash_mm: tuple[float, float] | None = None,
    dash_dot_mm: tuple[float, float, float, float] | None = None,
    font_family: str,
    font_mm: float,
    cap_ratio: float,
    tint: str | None = None,
    muted: str | None = None,
    texts: Mapping[str, str] | None = None,
    required_slots: Sequence[str] = (),
    library: Library | None = None,
) -> str:
    """Render a symbol as a `<g>` fragment in millimetres, with no `scale(`.

    The one transform is the `rotate(-90)` on the text element of a turned slot's string.
    A different output from `to_fragment`, whose contract is module units with the caller
    scaling. Here every coordinate and radius is multiplied by `module_mm`, and the stroke widths,
    the dash pattern and the font size are the caller's absolute millimetres, so they do not
    change with the module. Elements and their order are those of `to_fragment`. A text element
    ignores its `height`: it is drawn at `font_mm`, middle-anchored, with its capitals centred on
    its position.

    Args:
        symbol: The symbol to render, already oriented and repeated by the caller.
        module_mm: Millimetres per module unit.
        weights_mm: Stroke width in mm for each `Weight` the symbol uses. None takes
            `library.lines`; given, it wins over the library as a whole.
        dash_mm: Dash and gap lengths in mm of a dashed element. None takes
            `library.dash["dashed"]`.
        dash_dot_mm: Dash, gap, dot and gap lengths in mm of a dash-dot element. None takes
            `library.dash["dash_dot"]`, and is then an error if a dash-dot element is drawn.
        font_family: CSS font family of the text, escaped here for the attribute.
        font_mm: Font size in mm of every text element.
        cap_ratio: Capital height as a fraction of the font size; the baseline sits half of it
            below the text position.
        tint: Fill colour of the tinted closed polylines: `#rgb`, `#rrggbb` or a colour name.
            None draws them unfilled. Checked even when no element is tinted.
        muted: The colour a muted symbol is drawn in, or None. As in `to_fragment`, with the dash
            and gap of the normal stroke width taken from `weights_mm`; `dash_mm` and
            `dash_dot_mm` are then not used.
        texts: The string to draw in each slot, by slot id, or None to draw none. A slot without
            a string, or with an empty one, draws nothing. Each string follows the elements, in
            slot id order, at `font_mm` in `font_family`, aligned by the slot side (E start, W
            end, N and S middle; the baseline is half a capital below the slot point for E and W,
            on it for N and one capital below it for S). A turned slot (`turn`) reads bottom-up:
            N starts at the slot point, S ends there, E and W centre the text on it, and the text
            element carries `rotate(-90)` about its baseline point. It is never measured, shrunk
            or wrapped.
        required_slots: The slots the symbol must have a string for, as in `to_fragment`.
        library: The library whose `lines` and `dash` give each size the caller leaves None, so
            one call to `Library.with_settings` changes every width and dash drawn here.

    Returns:
        The `<g>...</g>` fragment text, ending with a single newline.

    Raises:
        UnknownNameError: A weight an element uses, or `Weight.NORMAL` when muted, is missing from
            `weights_mm` (or from `library.lines` when that is used); the key names it. Also a
            dashed element is drawn and neither `dash_mm` nor `library.dash["dashed"]` is there.
            Also a key of `texts` that is not a slot id
            of the symbol, checked before anything is drawn, also for an empty string.
        InvalidValueError: The tint or the muted colour is not a hex colour or a colour name, a
            dash-dot element is drawn and `dash_dot_mm` is None, or `texts` is given and misses a
            required slot; the message names it and the symbol.
    """
    check_tint(tint)
    check_colour("muted", muted)
    check_texts(symbol, texts, required_slots)
    own_widths = {} if library is None else library.lines
    dash = {} if library is None else library.dash
    mm = _Mm(
        module_mm,
        own_widths if weights_mm is None else weights_mm,
        dash.get("dashed") if dash_mm is None else dash_mm,
        dash.get("dash_dot") if dash_dot_mm is None else dash_dot_mm,
        font_family,
        font_mm,
        cap_ratio,
        muted,
    )
    lines = [
        group_open(muted),
        *(_element(mm, e, tint) for e in symbol.elements),
        *_slot_texts(mm, symbol, texts),
        "</g>",
    ]
    return "\n".join(lines) + "\n"
