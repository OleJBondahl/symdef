"""Drop the bound leads of ports the caller leaves unwired, or the ports themselves."""

from collections.abc import Iterable
from dataclasses import replace

from symdef.errors import UnknownNameError
from symdef.geometry import Line
from symdef.model import Slot, Symbol

_MARKING = "marking."


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


def _marking_of(slot: Slot) -> str | None:
    """Return the port id a `marking.<port>` slot belongs to, or None for any other slot."""
    return slot.id.removeprefix(_MARKING) if slot.id.startswith(_MARKING) else None


def only_ports(symbol: Symbol, ports: Iterable[str]) -> Symbol:
    """Return the symbol with only the listed ports, their leads and their marking slots.

    Every other port goes, with its bound lead and its `marking.<port>` slot, so the spare
    ports of a symbol leave no keep-out and no off-grid port behind. Other elements, slots and
    anchors stay, in order. Call it before `stretch`. A declared `keepout` stays as declared.
    Ids are those the symbol holds, so `1.a` after `table` or `repeat`.

    Raises:
        UnknownNameError: A listed id is not a port of the symbol; the message names it and the
            symbol.
    """
    wired = frozenset(ports)
    known = {port.id for port in symbol.ports}
    for name in sorted(wired - known):
        msg = (
            f"{name!r} is not a port of the symbol {symbol.name!r}; "
            f"its ports are {sorted(known)}; list only those"
        )
        raise UnknownNameError(msg)
    return replace(
        leads(symbol, wired),
        ports=tuple(p for p in symbol.ports if p.id in wired),
        slots=tuple(s for s in symbol.slots if _marking_of(s) in (None, *wired)),
    )
