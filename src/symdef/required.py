"""The slot ids `required_slots` ask of one symbol, the one expansion lint and fragments share."""

from collections.abc import Sequence

from symdef.model import Symbol, SymbolKind

PORT = "<port>"


def required_ids(symbol: Symbol, required_slots: Sequence[str]) -> list[tuple[str, str, str]]:
    """Return `(slot id, entry, port id)` for each slot a `kind = "symbol"` file must carry.

    An entry with `<port>` in it (`marking.<port>`) asks for one slot per port id; ports that share
    an id need one slot. The port id is empty for an entry without `<port>`. Another kind of
    symbol, or no entries, asks for nothing.
    """
    if symbol.kind is not SymbolKind.SYMBOL:
        return []
    port_ids = dict.fromkeys(port.id for port in symbol.ports)
    return [
        (entry.replace(PORT, port_id), entry, port_id)
        for entry in required_slots
        for port_id in (port_ids if PORT in entry else ("",))
    ]
