"""`text-outside-body`: a fixed text anchored in the body must lie wholly inside it (D90)."""

from symdef.boxes import element_box, elements_box
from symdef.font import FontMetrics
from symdef.geometry import Box, Point, Text
from symdef.model import Finding, Severity, Symbol

RULE = "text-outside-body"


def _shapes_box(symbol: Symbol, font: FontMetrics | None) -> Box | None:
    """Return the box of the symbol's drawn shapes (every element but a text), or None if none."""
    shapes = tuple(e for e in symbol.elements if not isinstance(e, Text))
    return elements_box(shapes, font) if shapes else None


def _anchored_in(at: Point, body: Box) -> bool:
    """Return whether a text's anchor point lies in the box."""
    return body.min.x <= at.x <= body.max.x and body.min.y <= at.y <= body.max.y


def text_outside_body(
    symbol: Symbol, font: FontMetrics | None, module_mm: float
) -> tuple[Finding, ...]:
    """Report each fixed text anchored inside the body whose measured box leaves the body.

    The text is measured with `font` at its own height and weight. The body is the box of the
    symbol's other elements. A text anchored outside the body, such as a label beside it, and a
    symbol with no other element are not checked.
    """
    body = _shapes_box(symbol, font)
    if body is None:
        return ()
    found: list[Finding] = []
    for i, element in enumerate(symbol.elements):
        if not isinstance(element, Text) or not _anchored_in(element.position, body):
            continue
        drawn = element_box(element, font)
        over = max(
            body.min.x - drawn.min.x,
            drawn.max.x - body.max.x,
            body.min.y - drawn.min.y,
            drawn.max.y - body.max.y,
        )
        if over > 0:
            message = (
                f"symbol {symbol.reference.number}: text {element.content!r} leaves the body box "
                f"by {over * module_mm:.3f} mm; shorten the text, lower its height, or enlarge "
                "the body"
            )
            found.append(Finding(RULE, Severity.ERROR, message, f"elements[{i}]"))
    return tuple(found)
