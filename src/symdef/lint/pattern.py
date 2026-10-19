"""`port-pattern`: one pattern port per edge, on a stretchable axis, unwired."""

from symdef.geometry import Direction
from symdef.lint.registry import quote, rule_finding
from symdef.model import Finding, Port, Symbol

_AXIS = {Direction.N: "x", Direction.S: "x", Direction.E: "y", Direction.W: "y"}


def _problem(symbol: Symbol, port: Port) -> str | None:
    """Return what is wrong with the pattern port, or None when it is fine."""
    name = quote(port.id)
    edge = port.direction.name
    axis = _AXIS[port.direction]
    other = next(
        (p for p in symbol.ports if p is not port and p.pattern and p.direction is port.direction),
        None,
    )
    if other is not None:
        return (
            f"the pattern port {name} shares edge {edge} with the pattern port "
            f"{quote(other.id)}; keep one pattern port per edge"
        )
    if not any(cut.axis == axis for cut in symbol.stretch):
        return (
            f"the pattern port {name} on edge {edge} needs a stretch cut on the {axis} axis; "
            f"declare one so the edge can grow"
        )
    if any(port.id in node.ports for node in symbol.nodes) or any(
        port.id in (path.from_port, path.to_port) for path in symbol.paths
    ):
        return (
            f"the pattern port {name} is named in a node or a path; "
            f"leave it out, as its copies are numbered after expansion"
        )
    return None


def port_pattern(symbol: Symbol) -> tuple[Finding, ...]:
    """Report each pattern port that cannot expand cleanly (D104).

    Three faults, one finding each: a second pattern port on the same edge (named ports may share
    it), no `stretch` cut on the edge's axis (N and S edges run along x, E and W along y), or the
    port named in an explicit node or a path. One finding per port, at `ports[i]`, the first fault
    only.
    """
    found: list[Finding] = []
    for index, port in enumerate(symbol.ports):
        message = _problem(symbol, port) if port.pattern else None
        if message is not None:
            found.append(rule_finding("port-pattern", message, f"ports[{index}]"))
    return tuple(found)
