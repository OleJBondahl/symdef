"""Repeat a symbol along +x: the only multi-pole mechanism."""

from collections.abc import Iterable
from dataclasses import replace
from string import Formatter

from symdef.errors import InvalidValueError
from symdef.geometry import Box, Element, Line, Point, Style, Weight
from symdef.model import Node, Path, Port, Slot, Symbol, nodes_of
from symdef.orient import translate

_DEFAULT_PITCH = 4
_LINK = "link"
_MARKING = "marking."

# A repeat in a part file stops here: the guide sets no bound, and a data file must not be able to
# ask for a million poles. `table` uses the same bound.
MAX_REPEAT = 64


def declared_union(boxes: Iterable[Box | None]) -> Box | None:
    """Return the box holding every declared box, or None when none is declared (D98)."""
    declared = tuple(b for b in boxes if b is not None)
    return Box.union(*declared) if declared else None


def pole_pitch(symbol: Symbol) -> float:
    """Return the spacing between poles in module units: the symbol's `pole_pitch`, else 4."""
    return symbol.pole_pitch or _DEFAULT_PITCH


def pole_port(k: int, port_id: str, port_format: str) -> str:
    """Return the id port `port_id` takes in pole `k` (counted from 1): `port_format` filled in."""
    return port_format.format(k=k, port=port_id)


def _template_fields(template: str) -> set[str] | None:
    """Return the field names of a format template, or None when it is not a well-formed one."""
    try:
        return {name for _, name, _, _ in Formatter().parse(template) if name}
    except ValueError:
        return None


def checked_port_format(port_format: object) -> str:
    """Return `port_format` when it is a template with exactly the fields `{k}` and `{port}`."""
    if not isinstance(port_format, str) or _template_fields(port_format) != {"k", "port"}:
        msg = (
            "a pole's port id needs port_format, a template with the fields {k} "
            f"and {{port}}, such as '{{k}}.{{port}}'; got {port_format!r}"
        )
        raise InvalidValueError(msg)
    return port_format


def pole_elements(elements: tuple[Element, ...], k: int, port_format: str) -> tuple[Element, ...]:
    """Return pole `k`'s elements, a bound lead's `port` renamed by `port_format` like its port."""
    return tuple(
        replace(e, port=pole_port(k, e.port, port_format))
        if isinstance(e, Line) and e.port is not None
        else e
        for e in elements
    )


def _pole_slots(slots: tuple[Slot, ...], k: int, port_format: str) -> tuple[Slot, ...]:
    """Return the slots pole `k` contributes: its marking slots renamed, the rest from pole 1."""
    return tuple(
        replace(s, id=_MARKING + pole_port(k, s.id.removeprefix(_MARKING), port_format))
        if s.id.startswith(_MARKING)
        else s
        for s in slots
        if k == 1 or s.id.startswith(_MARKING)
    )


def pole_parts(
    pole: Symbol, k: int, port_format: str
) -> tuple[tuple[Port, ...], tuple[Node, ...], tuple[Path, ...]]:
    """Return the ports, nodes and paths of pole `k` with every port id renamed by `port_format`."""
    return (
        tuple(replace(p, id=pole_port(k, p.id, port_format)) for p in pole.ports),
        tuple(
            replace(n, ports=tuple(pole_port(k, p, port_format) for p in n.ports))
            for n in nodes_of(pole)
        ),
        tuple(
            replace(
                p,
                from_port=pole_port(k, p.from_port, port_format),
                to_port=pole_port(k, p.to_port, port_format),
                through=p.through and k == 1,
            )
            for p in pole.paths
        ),
    )


def repeat(symbol: Symbol, n: int, *, port_format: str) -> Symbol:
    """Return `n` copies of a symbol placed along +x, as an ordinary symbol.

    Pole k (from 1) is the symbol translated by `((k - 1) * pitch, 0)`, where the pitch is the
    symbol's `pole_pitch`, default 4. Ports, and the paths, nodes and bound leads that name them,
    are renamed by `port_format`, a template with the fields `{k}` and `{port}` that the caller
    supplies (a pole prefix is an electrical convention; symdef keeps none, D121); every node is
    listed explicitly, `potential` kept. Marking slots (`marking.in` becomes `marking.` plus the
    formatted id) repeat per pole; `tag`, `value` and any other slot come from pole 1 only.
    Only pole 1's path keeps `through`; a symbol with no through path repeats just the same, its
    poles all without one (D106). Pole 1's anchors become the result's anchors, and if one
    is `link` and `n > 1` a dashed line joins pole 1's `link` to pole n's. `pole_pitch` becomes
    `n * pitch`; everything else is carried over.

    Args:
        symbol: A symbol in base orientation.
        n: The pole count, at least 1.
        port_format: The template of a pole's port id, such as `"{k}.{port}"`; required.

    Returns:
        The repeated symbol; with `n = 1` it is the symbol with renamed ports and slots.

    Raises:
        InvalidValueError: If `n` is below 1, or `port_format` is not a template with
            exactly the fields `{k}` and `{port}`.
    """
    port_format = checked_port_format(port_format)
    if n < 1:
        msg = f"the pole count must be at least 1, got {n}"
        raise InvalidValueError(msg)
    pitch = pole_pitch(symbol)
    poles = tuple(translate(symbol, (k - 1) * pitch, 0) for k in range(1, n + 1))
    parts = tuple(pole_parts(pole, k, port_format) for k, pole in enumerate(poles, start=1))
    link = next((a for a in symbol.anchors if a.id == _LINK), None)
    dashes = ()
    if link is not None and n > 1:
        end = Point(link.position.x + (n - 1) * pitch, link.position.y)
        dashes = (Line(link.position, end, Weight.NORMAL, Style.DASHED),)
    return replace(
        symbol,
        elements=tuple(
            e
            for k, pole in enumerate(poles, start=1)
            for e in pole_elements(pole.elements, k, port_format)
        )
        + dashes,
        ports=tuple(p for ports, _, _ in parts for p in ports),
        nodes=tuple(node for _, nodes, _ in parts for node in nodes),
        paths=tuple(path for _, _, paths in parts for path in paths),
        anchors=poles[0].anchors,
        slots=tuple(
            s
            for k, pole in enumerate(poles, start=1)
            for s in _pole_slots(pole.slots, k, port_format)
        ),
        pole_pitch=n * pitch,
        body=declared_union(p.body for p in poles),
        keepout=declared_union(p.keepout for p in poles),
    )
