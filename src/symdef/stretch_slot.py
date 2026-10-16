"""A slot under `stretch`: each box corner moves by the shares of the cuts it lies beyond."""

from collections.abc import Callable
from dataclasses import replace
from typing import Literal

from symdef.boxes import slot_box
from symdef.geometry import Direction, Point
from symdef.model import Slot

type Axis = Literal["x", "y"]
type Role = Literal["lo", "hi", "mid"]

# Where the slot position stands on the box along (x, y): low edge, high edge or middle.
_ROLES: dict[Direction, tuple[Role, Role]] = {
    Direction.E: ("lo", "mid"),
    Direction.W: ("hi", "mid"),
    Direction.N: ("mid", "hi"),
    Direction.S: ("mid", "lo"),
}


def _place(
    edges: tuple[float, float],
    here: float,
    size: float,
    role: Role,
    shift: Callable[[float], float],
) -> tuple[float, float]:
    """Return the moved position coordinate and the stretched box size along the axis.

    A box with both edges moving alike keeps its size and its position moves by its own shift,
    as in 0.9.0; a box across a cut grows by the difference of its edges' shifts.
    """
    low, high = edges
    low_shift, high_shift = shift(low), shift(high)
    if low_shift == high_shift:
        return (here + shift(here) if low_shift else here), size
    moved = {"lo": low + low_shift, "hi": high + high_shift}
    middle = (low + low_shift + high + high_shift) / 2
    return moved.get(role, middle), size + (high_shift - low_shift)


def stretch_slot(slot: Slot, axis: Axis, shift: Callable[[float], float]) -> Slot:
    """Return the slot with both box corners and the position moved along the axis.

    `slot_box` of the result is exactly the moved corners of the old box.
    """
    box = slot_box(slot)
    x_role, y_role = _ROLES[slot.side]
    width, height = slot.box
    if axis == "x":
        x, width = _place((box.min.x, box.max.x), slot.position.x, width, x_role, shift)
        y = slot.position.y
    else:
        y, height = _place((box.min.y, box.max.y), slot.position.y, height, y_role, shift)
        x = slot.position.x
    return replace(slot, position=Point(x, y), box=(width, height))
