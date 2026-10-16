"""A slot under `stretch`: its position moves by the shares of the cuts it lies beyond (D69)."""

from collections.abc import Callable
from dataclasses import replace
from typing import Literal

from symdef.boxes import slot_box
from symdef.geometry import Point
from symdef.model import Centre, Slot

type Axis = Literal["x", "y"]


def _place(
    edges: tuple[float, float],
    here: float,
    size: float,
    *,
    centred: bool,
    shift: Callable[[float], float],
) -> tuple[float, float]:
    """Return the moved position coordinate and the stretched box size along the axis.

    A box across a cut grows by the difference of its edges' shifts. The position moves by its
    own shift, as in 0.9.0; only a `C` slot sits at the middle of its moved edges (D68).
    """
    low, high = edges
    low_shift, high_shift = shift(low), shift(high)
    if centred:
        here = (low + low_shift + high + high_shift) / 2
    else:
        here += shift(here)
    return here, size + (high_shift - low_shift)


def stretch_slot(slot: Slot, axis: Axis, shift: Callable[[float], float]) -> Slot:
    """Return the slot with its box grown and its position moved along the axis."""
    box = slot_box(slot)
    centred = slot.side is Centre.C
    width, height = slot.box
    if axis == "x":
        x, width = _place(
            (box.min.x, box.max.x), slot.position.x, width, centred=centred, shift=shift
        )
        y = slot.position.y
    else:
        y, height = _place(
            (box.min.y, box.max.y), slot.position.y, height, centred=centred, shift=shift
        )
        x = slot.position.x
    return replace(slot, position=Point(x, y), box=(width, height))
