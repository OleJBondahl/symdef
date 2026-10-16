"""The `[lines]` table of `library.toml`: the check that every wire weight has a width."""

from collections.abc import Mapping, Sequence

from symdef.geometry import Weight
from symdef.model import WireStyle


def lines_problems(wires: Sequence[WireStyle], lines: Mapping[Weight, float]) -> tuple[str, ...]:
    """Return one message per wire weight that has no width in `lines`.

    A library with no `[lines]` table (empty `lines`) declares no widths, so nothing is checked.
    """
    if not lines:
        return ()
    used = sorted({w.weight for w in wires}, key=lambda weight: weight.value)
    return tuple(
        f"wire weight {weight.name.lower()!r} has no width: add "
        f"`{weight.name.lower()} = <millimetres>` to [lines]"
        for weight in used
        if weight not in lines
    )
