"""Three hand-built symbols whose `to_fragment` and `to_svg` bytes `fixtures/svg_golden` pins."""

from symdef import (
    Arc,
    Circle,
    Direction,
    Fill,
    Line,
    Point,
    Polyline,
    Port,
    Reference,
    Status,
    Style,
    Symbol,
    SymbolKind,
    Text,
    Weight,
)


def _sym(name, elements, ports=()):
    return Symbol(
        name=name,
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=elements,
        ports=ports,
    )


GOLDEN_SYMBOLS = {
    "box": _sym(
        "box",
        (
            Polyline((Point(0, 0), Point(4, 0), Point(4, 2), Point(0, 2)), closed=True),
            Line(Point(0, 1), Point(-1, 1)),
        ),
        (Port("1", Point(-1, 1), Direction.W),),
    ),
    "round": _sym(
        "round",
        (
            Circle(Point(2, 2), 1.5, fill=Fill.SOLID),
            Arc(Point(2, 2), 2, 0, 90, weight=Weight.THICK),
            Arc(Point(2, 2), 0.5, 0, 0, style=Style.DASHED),
        ),
    ),
    "labelled": _sym(
        "labelled",
        (
            Polyline((Point(0, 0), Point(3, 0), Point(3, 3)), style=Style.DASHED),
            Text("A<&>1", Point(1.5, 1.5), height=0.8),
        ),
    ),
}
