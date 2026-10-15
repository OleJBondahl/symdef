"""SVG fragment in millimetres: the exact-size output, with no scale transform."""

from collections.abc import Mapping
from typing import NamedTuple
from xml.sax.saxutils import quoteattr

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
from symdef.model import Symbol
from symdef.svg import _FULL_TURN, _GROUP_OPEN, _HALF_TURN, _content, _num, check_tint


class _Mm(NamedTuple):
    """The caller's physical sizes, as `to_fragment_mm` receives them."""

    module: float
    weights: Mapping[Weight, float]
    dash: tuple[float, float]
    dash_dot: tuple[float, float, float, float] | None
    family: str
    font: float
    cap_ratio: float

    def xy(self, p: Point) -> tuple[str, str]:
        """Return a point as two millimetre numbers."""
        return _num(p.x * self.module), _num(p.y * self.module)

    def stroke(
        self,
        weight: Weight,
        fill: Fill = Fill.NONE,
        style: Style = Style.SOLID,
        tint: str | None = None,
    ) -> str:
        """Return the closing attributes of a stroked shape, widths and dashes in mm."""
        dashed = self.dashes(style)
        if fill is Fill.SOLID:
            solid = ' fill="#000"'
        elif fill is Fill.TINT:
            colour = "none" if tint is None else tint
            solid = f' fill="{colour}"'
        else:
            solid = ""
        width = _num(self.weights[weight])
        return f'stroke-width="{width}"{dashed}{solid}/>'

    def dashes(self, style: Style) -> str:
        """Return the dash attribute of a line style, or nothing for a solid line."""
        if style is Style.DASH_DOT:
            if self.dash_dot is None:
                message = "dash_dot_mm is required to draw a dash_dot element"
                raise ValueError(message)
            return f' stroke-dasharray="{" ".join(_num(n) for n in self.dash_dot)}"'
        if style is Style.DASHED:
            return f' stroke-dasharray="{_num(self.dash[0])} {_num(self.dash[1])}"'
        return ""

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
    y = _num(text.position.y * mm.module + mm.cap_ratio * mm.font / 2)
    return (
        f'<text x="{x}" y="{y}" font-size="{_num(mm.font)}" text-anchor="middle" fill="#000" '
        f'stroke="none" font-family={quoteattr(mm.family)}>{_content(text.content)}</text>'
    )


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
    weights_mm: Mapping[Weight, float],
    dash_mm: tuple[float, float],
    dash_dot_mm: tuple[float, float, float, float] | None = None,
    font_family: str,
    font_mm: float,
    cap_ratio: float,
    tint: str | None = None,
) -> str:
    """Render a symbol as a `<g>` fragment in millimetres, with no `scale(` and no transform.

    A different output from `to_fragment`, whose contract is module units with the caller
    scaling. Here every coordinate and radius is multiplied by `module_mm`, and the stroke widths,
    the dash pattern and the font size are the caller's absolute millimetres, so they do not
    change with the module. Elements and their order are those of `to_fragment`. A text element
    ignores its `height`: it is drawn at `font_mm`, middle-anchored, with its capitals centred on
    its position.

    Args:
        symbol: The symbol to render, already oriented and repeated by the caller.
        module_mm: Millimetres per module unit.
        weights_mm: Stroke width in mm for each `Weight` the symbol uses.
        dash_mm: Dash and gap lengths in mm of a dashed element.
        dash_dot_mm: Dash, gap, dot and gap lengths in mm of a dash-dot element; None when the
            symbol has none.
        font_family: CSS font family of the text, escaped here for the attribute.
        font_mm: Font size in mm of every text element.
        cap_ratio: Capital height as a fraction of the font size; the baseline sits half of it
            below the text position.
        tint: Fill colour of the tinted closed polylines: `#rgb`, `#rrggbb` or a colour name.
            None draws them unfilled. Checked even when no element is tinted.

    Returns:
        The `<g>...</g>` fragment text, ending with a single newline.

    Raises:
        KeyError: A weight an element uses is missing from `weights_mm`; the key names it.
        ValueError: The tint is not a hex colour or a colour name, or a dash-dot element is drawn
            and `dash_dot_mm` is None.
    """
    check_tint(tint)
    mm = _Mm(module_mm, weights_mm, dash_mm, dash_dot_mm, font_family, font_mm, cap_ratio)
    lines = [_GROUP_OPEN, *(_element(mm, e, tint) for e in symbol.elements), "</g>"]
    return "\n".join(lines) + "\n"
