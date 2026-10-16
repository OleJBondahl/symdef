"""Drop the bound leads of ports the caller leaves unwired."""

from collections.abc import Iterable
from dataclasses import replace

from symdef.errors import UnknownNameError
from symdef.geometry import Line
from symdef.model import Symbol


def leads(symbol: Symbol, ports: Iterable[str]) -> Symbol:
    """Return the symbol without the bound leads of every port not in `ports`.

    A `Line` whose `port` is None, a `Line` bound to a listed port and every other element stay,
    in order. The caller names the wired ports; ids are those the symbol holds, so `1.a` after
    `table` or `repeat`.

    Raises:
        UnknownNameError: A listed id is not a port of the symbol; the key names it.
    """
    wired = frozenset(ports)
    known = {port.id for port in symbol.ports}
    for name in sorted(wired - known):
        msg = (
            f"{name!r} is not a port of the symbol; its ports are {sorted(known)}; list only those"
        )
        raise UnknownNameError(msg)
    kept = tuple(
        e for e in symbol.elements if not (isinstance(e, Line) and e.port not in (None, *wired))
    )
    return replace(symbol, elements=kept)
