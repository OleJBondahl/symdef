"""`measure`: a symbol turned to an orientation, as whole grid divisions of a library's grid."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from symdef.boxes import body_box, slot_box
from symdef.errors import InvalidValueError
from symdef.geometry import Box, Direction
from symdef.gridtypes import GridBox, GridPoint, GridPort
from symdef.model import Library, Symbol
from symdef.orient import Orientation, orient
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


def measure(
    symbol: Symbol,
    orientation: Orientation,
    library: Library,
    texts: Mapping[str, str] | None = None,
    text_height: float | None = None,
) -> Measure:
    """Return the symbol turned to `orientation`, measured in divisions of `library.grid`.

    The symbol is oriented first. Extents (the body and every slot box) round outward, so a
    caller never rounds; ports are positions and must sit on the grid. Text is measured with
    `library.font`: the body's own text, and a slot's string when `texts` has one for its id
    (at `text_height`). A slot with no string is its reserved box.

    Raises:
        InvalidValueError: If `texts` is given without `text_height`, or a port is off the grid.
        UnknownNameError: If a key of `texts` is not a slot id of the symbol.
    """
    if texts and text_height is None:
        msg = "texts needs text_height to measure a string; pass text_height="
        raise InvalidValueError(msg)
    check_texts(symbol, texts)
    turned = orient(symbol, orientation)
    body = _extent(library, body_box(turned, library.font))
    slots = {
        s.id: _extent(library, slot_box(s, (texts or {}).get(s.id), text_height, library.font))
        for s in turned.slots
    }
    ports = {
        p.id: _port(library, p.id, p.position.x, p.position.y, p.direction) for p in turned.ports
    }
    return Measure(body, GridBox.union(body, *slots.values()), slots, ports)
