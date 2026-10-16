"""`to_placed_fragment`: a symbol drawn in millimetres where a grid position puts it."""

from collections.abc import Mapping, Sequence

from symdef.geometry import Weight
from symdef.gridtypes import GridPoint
from symdef.model import Library, Symbol
from symdef.orient import Orientation, orient
from symdef.svg import _num
from symdef.svg_mm import to_fragment_mm
from symdef.units import from_divisions


def to_placed_fragment(  # noqa: PLR0913 - the placement and one physical size per keyword
    symbol: Symbol,
    orientation: Orientation,
    at: GridPoint,
    library: Library,
    *,
    module_mm: float,
    weights_mm: Mapping[Weight, float],
    dash_mm: tuple[float, float],
    dash_dot_mm: tuple[float, float, float, float] | None = None,
    font_family: str,
    font_mm: float,
    cap_ratio: float,
    tint: str | None = None,
    muted: str | None = None,
    texts: Mapping[str, str] | None = None,
    required_slots: Sequence[str] = (),
) -> str:
    """Return the symbol turned to `orientation` and drawn in mm with its origin at `at`.

    It is `to_fragment_mm` of the oriented symbol inside one `<g transform="translate(X Y)">`,
    where X and Y are `at` in divisions of `library.grid` times `module_mm`, in millimetres. The
    other keywords are those of `to_fragment_mm`, which this replaces for a placed drawing.

    Raises:
        UnknownNameError: As `to_fragment_mm`.
        InvalidValueError: As `to_fragment_mm`.
    """
    body = to_fragment_mm(
        orient(symbol, orientation),
        module_mm=module_mm,
        weights_mm=weights_mm,
        dash_mm=dash_mm,
        dash_dot_mm=dash_dot_mm,
        font_family=font_family,
        font_mm=font_mm,
        cap_ratio=cap_ratio,
        tint=tint,
        muted=muted,
        texts=texts,
        required_slots=required_slots,
    )
    x, y = (_num(from_divisions(library.grid, n) * module_mm) for n in (at.x, at.y))
    return f'<g transform="translate({x} {y})">\n{body}</g>\n'
