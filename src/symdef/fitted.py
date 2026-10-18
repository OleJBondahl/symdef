"""`fitted_table`: a table whose columns are as wide as the widest text set in them (D94)."""

from collections.abc import Mapping, Sequence
from dataclasses import replace

from symdef.boxes import body_box, slot_box
from symdef.errors import InvalidValueError
from symdef.geometry import Box
from symdef.model import Library, Slot, Stretch, Symbol
from symdef.slottext import text_box
from symdef.stretch import Axis, stretch
from symdef.svg import check_texts
from symdef.table import table
from symdef.units import ceil_divisions, from_divisions

_NOISE = 1e-9


def _along(box: Box, axis: Axis) -> float:
    """Return the box's extent along the axis."""
    return box.width if axis == "x" else box.height


def _low(box: Box, axis: Axis) -> float:
    """Return the box's low edge on the axis."""
    return box.min.x if axis == "x" else box.min.y


def _cut_across(symbol: Symbol, slot: Slot, axis: Axis) -> Stretch:
    """Return the symbol's cut on the axis that lies inside the slot's reserved box."""
    box = slot_box(slot)
    low, high = _low(box, axis), _low(box, axis) + _along(box, axis)
    for cut in symbol.stretch:
        if cut.axis == axis and low < cut.at < high:
            return cut
    msg = (
        f"{symbol.name}: the slot {slot.id!r} has no stretch cut across its box on the "
        f"{axis} axis; add a [[stretch]] on {axis} inside the slot's box so its column can grow"
    )
    raise InvalidValueError(msg)


def _growth(  # noqa: PLR0913 - the symbol, axis, texts, library, height and the leniency
    symbol: Symbol,
    axis: Axis,
    texts: Mapping[str, str],
    library: Library,
    height: float,
    *,
    lenient: bool = False,
) -> dict[float, float]:
    """Return how far each cut must grow: each text's extent rounded up, less its slot's.

    The key is the cut's `at`. A text that fits its slot's reserved box asks for no growth; when
    `lenient`, it also needs no cut, which `fitted_symbol` allows (D95).
    """
    slots = {s.id: s for s in symbol.slots}
    grid, wanted = library.grid, {}
    for slot_id, text in texts.items():
        slot = slots[slot_id]
        need = from_divisions(
            grid,
            ceil_divisions(grid, _along(text_box(slot, text, height, library.font, grid), axis)),
        )
        grow = need - _along(slot_box(slot), axis)
        if lenient and grow <= _NOISE:
            continue
        cut = _cut_across(symbol, slot, axis)
        wanted[cut.at] = max(wanted.get(cut.at, 0.0), grow)
    return {at: grow for at, grow in wanted.items() if grow > _NOISE}


def _grown(symbol: Symbol, axis: Axis, growth: Mapping[float, float]) -> Symbol:
    """Return the symbol stretched along the axis, each cut in `growth` taking its own growth."""
    if not growth:
        return symbol
    missing = sorted(set(growth) - {c.at for c in symbol.stretch if c.axis == axis})
    if missing:
        msg = (
            f"{symbol.name}: no stretch cut on the {axis} axis at {missing[0]}, where the rows "
            f"grow; add a [[stretch]] on {axis} at {missing[0]}"
        )
        raise InvalidValueError(msg)
    cuts = tuple(Stretch(axis, at, grow) for at, grow in sorted(growth.items()))
    kept = tuple(s for s in symbol.stretch if s.axis != axis)
    natural = _along(body_box(symbol), axis)
    return stretch(replace(symbol, stretch=kept + cuts), axis, natural + sum(growth.values()))


def _merge(*growths: Mapping[float, float]) -> dict[float, float]:
    """Return the largest growth asked of each cut."""
    out: dict[float, float] = {}
    for growth in growths:
        for at, grow in growth.items():
            out[at] = max(out.get(at, 0.0), grow)
    return out


def fitted_table(  # noqa: PLR0913 - the ruled signature: row, axis, texts, library, height and a head
    row: Symbol,
    axis: Axis,
    texts: Sequence[Mapping[str, str]],
    library: Library,
    text_height: float,
    *,
    head: Symbol | None = None,
    head_texts: Mapping[str, str] | None = None,
) -> Symbol:
    """Return `table(row, len(texts), axis, head)` with each column as wide as its widest text.

    Rows stack along `axis`; a column runs across it, so it grows along the other axis. A column
    is a slot of the row with a `[[stretch]]` cut across its box on that axis. Its text is set in
    `library.font` at `text_height` (module units); the widest text over all rows, and over the
    head's texts, is rounded up to whole grid divisions. The cut grows by that less the slot's
    reserved extent, never below zero, so the row's own pads stay. The growth goes through
    `stretch`; the head grows at the same cuts when it has them. The result is an ordinary symbol.

    Args:
        row: A symbol in base orientation, a slot and a cut across it for each column.
        axis: "x" or "y", the way the rows stack.
        texts: One mapping of slot id to text for each row; its length is the row count.
        library: The library whose font and grid measure the texts.
        text_height: The text height in module units, above zero.
        head: A symbol placed once before the rows, or None.
        head_texts: Slot id of the head to its text, or None; each counts in its column.

    Returns:
        The table, as `table` returns it.

    Raises:
        UnknownNameError: If a text names a slot its symbol does not have.
        InvalidValueError: If the library has no font, `text_height` is not above zero, a text's
            slot has no cut across its box, the head lacks a cut where the rows grow, or the
            row count is out of range.
    """
    if library.font is None:
        msg = "fitted_table needs a library with a font to measure the texts; load one with [font]"
        raise InvalidValueError(msg)
    if not text_height > 0:
        msg = f"fitted_table needs a text height above zero, got {text_height!r}"
        raise InvalidValueError(msg)
    if head_texts and head is None:
        msg = "head_texts needs a head to set them in; pass head= or drop head_texts"
        raise InvalidValueError(msg)
    cross: Axis = "y" if axis == "x" else "x"
    for row_texts in texts:
        check_texts(row, row_texts)
    growth = _merge(*(_growth(row, cross, t, library, text_height) for t in texts))
    if head is not None and head_texts:
        check_texts(head, head_texts)
        growth = _merge(growth, _growth(head, cross, head_texts, library, text_height))
    if head is not None and any(s.axis == cross for s in head.stretch):
        head = _grown(head, cross, growth)
    return table(_grown(row, cross, growth), len(texts), axis, head)


def fitted_symbol(
    symbol: Symbol, texts: Mapping[str, str], library: Library, text_height: float
) -> Symbol:
    """Return `symbol` stretched on each axis so every slot in `texts` holds its text (D95).

    A text is measured as `text_box` does in `library.font` at `text_height` (module units), a
    multi-line text by its whole block, and a turned slot's text along y. The extent is rounded up
    to whole grid divisions; a cut across the slot's box grows by that less the slot's reserved
    extent. A slot whose text fits asks for nothing and needs no cut. The growth goes through
    `stretch`; the result is an ordinary symbol.

    Raises:
        UnknownNameError: If a text names a slot the symbol does not have.
        InvalidValueError: If the library has no font, `text_height` is not above zero, or a slot
            that must grow has no cut across its box on that axis.
    """
    if library.font is None:
        msg = "fitted_symbol needs a library with a font to measure the texts; load one with [font]"
        raise InvalidValueError(msg)
    if not text_height > 0:
        msg = f"fitted_symbol needs a text height above zero, got {text_height!r}"
        raise InvalidValueError(msg)
    check_texts(symbol, texts)
    for axis in ("x", "y"):
        growth = _growth(symbol, axis, texts, library, text_height, lenient=True)
        symbol = _grown(symbol, axis, growth)
    return symbol
