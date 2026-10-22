"""`measure`: a symbol turned to an orientation, as whole grid divisions of a library's grid."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from symdef.boxes import body_box, keepout_box, side_box, slot_box
from symdef.errors import InvalidValueError
from symdef.geometry import Box, Direction
from symdef.gridtypes import GridBox, GridPoint, GridPort
from symdef.model import Library, Slot, Symbol
from symdef.orient import Orientation, orient
from symdef.stretch import Axis
from symdef.stretch import stretch as stretch_symbol
from symdef.svg import check_texts
from symdef.units import ceil_divisions, to_divisions


@dataclass(frozen=True, slots=True)
class Measure:
    """What a symbol takes up and where its ports are, in whole grid divisions.

    Attributes:
        body: The body box. A box's `max` is the extent rounded up, its `min` rounded down.
        keepout: The body united with every slot box.
        slots: Slot id to its box, with the text measured when `measure` was given one.
        ports: Port id to its position and its direction after the turn.
    """

    body: GridBox
    keepout: GridBox
    slots: Mapping[str, GridBox]
    ports: Mapping[str, GridPort]

    def __post_init__(self) -> None:
        """Make `slots` and `ports` read-only, so the value cannot change after it is built."""
        object.__setattr__(self, "slots", MappingProxyType(dict(self.slots)))
        object.__setattr__(self, "ports", MappingProxyType(dict(self.ports)))


def _extent(library: Library, box: Box) -> GridBox:
    """Round a box outward to whole divisions: the min down, the max up."""
    grid = library.grid
    return GridBox(
        GridPoint(-ceil_divisions(grid, -box.min.x), -ceil_divisions(grid, -box.min.y)),
        GridPoint(ceil_divisions(grid, box.max.x), ceil_divisions(grid, box.max.y)),
    )


def _port(library: Library, port_id: str, x: float, y: float, direction: Direction) -> GridPort:
    """Return a port in divisions; a position off the grid raises naming the port."""
    try:
        return GridPort(
            port_id, to_divisions(library.grid, x), to_divisions(library.grid, y), direction
        )
    except InvalidValueError as error:
        msg = f"port {port_id!r}: {error}; move the port onto the grid"
        raise InvalidValueError(msg) from error


def _slot_with_attached(
    slot: Slot,
    texts: Mapping[str, str] | None,
    text_height: float | None,
    library: Library,
    attach: Mapping[str, Symbol] | None,
) -> Box:
    """Return the slot's box, grown to hold the symbol attached to it, if any."""
    box = slot_box(slot, (texts or {}).get(slot.id), text_height, library.font, library.grid)
    if not attach or slot.id not in attach:
        return box
    inner = keepout_box(attach[slot.id], library.font)
    placed = side_box(
        slot.position, slot.side, inner.max.x - inner.min.x, inner.max.y - inner.min.y
    )
    return Box.union(box, placed)


def _stretched(symbol: Symbol, lengths: Mapping[Axis, float] | None, library: Library) -> Symbol:
    """Return the symbol stretched along each axis of `lengths` to its length (D111)."""
    for axis, length in (lengths or {}).items():
        symbol = stretch_symbol(symbol, axis, length, grid=library.grid)
    return symbol


def measure(  # noqa: PLR0913 - the ruled signature: symbol, view, library and three options
    symbol: Symbol,
    orientation: Orientation,
    library: Library,
    texts: Mapping[str, str] | None = None,
    text_height: float | None = None,
    *,
    attach: Mapping[str, Symbol] | None = None,
    stretch: Mapping[Axis, float] | None = None,
) -> Measure:
    """Return the symbol turned to `orientation`, measured in divisions of `library.grid`.

    The symbol is oriented first. Extents (the body and every slot box) round outward, so a
    caller never rounds; ports are positions and must sit on the grid. Text is measured with
    `library.font`: the body's own text, and a slot's string when `texts` has one for its id
    (at `text_height`). A slot with no string is its reserved box. A symbol in `attach` under a
    slot id has its keep-out box placed at the turned slot's point and side, as a slot's reserved
    box is, and united with that slot's box, so `slots[id]` and `keepout` hold it. The attached
    box is never rotated, as a slot's box is not. `stretch` maps an axis to a body length: the
    symbol is stretched so (`grid=library.grid`) before it is turned (D111).

    Raises:
        InvalidValueError: If `texts` is given without `text_height`, or a port is off the grid,
            or `stretch()` refuses a length.
        UnknownNameError: If a key of `texts` or `attach` is not a slot id of the symbol.
    """
    if texts and text_height is None:
        msg = "texts needs text_height to measure a string; pass text_height="
        raise InvalidValueError(msg)
    check_texts(symbol, texts)
    check_texts(symbol, dict.fromkeys(attach or {}, ""))
    turned = orient(_stretched(symbol, stretch, library), orientation)
    body = _extent(library, body_box(turned, library.font))
    slots = {
        s.id: _extent(library, _slot_with_attached(s, texts, text_height, library, attach))
        for s in turned.slots
    }
    ports = {
        p.id: _port(library, p.id, p.position.x, p.position.y, p.direction) for p in turned.ports
    }
    return Measure(body, GridBox.union(body, *slots.values()), slots, ports)
