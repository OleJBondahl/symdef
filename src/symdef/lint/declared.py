"""`element-outside-body`: a drawn shape must lie wholly inside a declared body (D98)."""

from symdef.boxes import element_box
from symdef.geometry import Text
from symdef.lint.registry import rule_finding
from symdef.model import Finding, Symbol

# The distance a shape may overshoot a declared edge: the guide's tolerance for derived values.
_TOLERANCE = 1e-9


def element_outside_body(symbol: Symbol) -> tuple[Finding, ...]:
    """Report each shape whose extent leaves the symbol's declared `body`.

    A symbol that declares no body is not checked. A text is left to `text-outside-body`, which
    measures it with the library's font; every other element is measured by `element_box`.
    """
    body = symbol.body
    if body is None:
        return ()
    found: list[Finding] = []
    for i, element in enumerate(symbol.elements):
        if isinstance(element, Text):
            continue
        box = element_box(element)
        over = max(
            body.min.x - box.min.x,
            box.max.x - body.max.x,
            body.min.y - box.min.y,
            box.max.y - body.max.y,
        )
        if over > _TOLERANCE:
            message = (
                f"symbol {symbol.name!r}: elements[{i}] ({type(element).__name__.lower()}) leaves "
                f"the declared body by {over:g} M; enlarge `body` or move the element inside it"
            )
            found.append(rule_finding("element-outside-body", message, f"elements[{i}]"))
    return tuple(found)
