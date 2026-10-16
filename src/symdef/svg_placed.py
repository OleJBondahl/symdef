"""`to_placed_fragment`: a symbol drawn where a grid position puts it, no caller conversion."""

from collections.abc import Mapping, Sequence

from symdef.gridtypes import GridPoint
from symdef.model import Library, Symbol
from symdef.orient import Orientation, orient
from symdef.svg import _num, to_fragment
from symdef.units import from_divisions


def to_placed_fragment(  # noqa: PLR0913 - the placement and the four draw options are separate things
    symbol: Symbol,
    orientation: Orientation,
    at: GridPoint,
    library: Library,
    *,
    tint: str | None = None,
    muted: str | None = None,
    texts: Mapping[str, str] | None = None,
    required_slots: Sequence[str] = (),
) -> str:
    """Return the symbol turned to `orientation` and drawn with its origin at `at`.

    It is `to_fragment` of the oriented symbol inside one `<g transform="translate(X Y)">`, where
    X and Y are `at` turned into module units by `library.grid`. The options are those of
    `to_fragment`. The float forms (`to_fragment`, `to_fragment_mm`, `to_svg`) are unchanged.

    Raises:
        UnknownNameError: A key of `texts` is not a slot id of the symbol.
        InvalidValueError: As `to_fragment`.
    """
    body = to_fragment(
        orient(symbol, orientation),
        tint=tint,
        muted=muted,
        texts=texts,
        required_slots=required_slots,
    )
    x, y = (_num(from_divisions(library.grid, n)) for n in (at.x, at.y))
    return f'<g transform="translate({x} {y})">\n{body}</g>\n'
