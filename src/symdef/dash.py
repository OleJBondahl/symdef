"""The `[dash]` table of `library.toml`: named dash patterns in millimetres (D115)."""

from collections.abc import Iterable, Mapping, Sequence

from symdef.geometry import Arc, Line, Polyline, Style
from symdef.model import Symbol, WireStyle

DASHED = "dashed"
DASH_DOT = "dash_dot"
# The key each non-solid `Style` reads, and how many lengths its pattern has.
REQUIRED = {Style.DASHED: (DASHED, 2), Style.DASH_DOT: (DASH_DOT, 4)}


def pattern_problem(name: str, pattern: Sequence[object]) -> str | None:
    """Return what is wrong with one pattern, or None.

    A pattern is an even count of at least 2 lengths, each above zero. `dashed` has exactly 2
    and `dash_dot` exactly 4.
    """
    needed = next((n for key, n in REQUIRED.values() if key == name), None)
    count = len(pattern)
    if needed is not None and count != needed:
        return f"{name!r} must have exactly {needed} lengths, got {count}"
    if count < 2 or count % 2:  # noqa: PLR2004 - a dash and a gap make a pair
        return f"{name!r} must have an even number of lengths, at least 2, got {count}"
    return None


def dash_problems(
    symbols: Iterable[Symbol],
    wires: Iterable[WireStyle],
    dash: Mapping[str, Sequence[float]],
) -> tuple[str, ...]:
    """Return one message per style a symbol element or wire style uses whose pattern is missing."""
    used = {w.style for w in wires}
    used.update(
        e.style for s in symbols for e in s.elements if isinstance(e, Line | Polyline | Arc)
    )
    return tuple(
        f"style {style.value!r} is used but [dash] has no {key!r}: add "
        f"`{key} = [...]` in millimetres"
        for style, (key, _) in REQUIRED.items()
        if style in used and key not in dash
    )
