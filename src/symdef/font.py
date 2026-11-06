"""Font metrics as library data, and the width of a text measured with them."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from symdef.errors import InvalidValueError
from symdef.geometry import TEXT_WEIGHTS, Weight
from symdef.units import Grid, ceil_divisions

# What a text measures when a library declares no font: 0.6 em per character, cap height 0.72 em.
DEFAULT_ADVANCE_EM = 0.6
DEFAULT_CAP_EM = 0.72
# Rows of a multi-line text sit this many cap heights apart: one cap height and half of one more.
LINE_PITCH = 1.5


@dataclass(frozen=True, slots=True)
class FontMetrics:
    """The measures of one font, in the font's own units; `units_per_em` is one em.

    Attributes:
        name: The font's name, for the record; it changes no measure.
        units_per_em: How many font units make one em, the text height.
        cap_height: Height of a capital letter above the baseline, in font units.
        ascent: Height of the tallest glyph above the baseline, in font units.
        descent: Depth of the lowest glyph below the baseline, in font units.
        advances: One table per text weight (`TEXT_WEIGHTS`): the advance of each character, in
            font units.
        default_advance: One advance per text weight: what a character its table does not list
            takes, so a bold text charges the bold face's own default (D119).
        heights: Capital heights in millimetres by name, such as `smallest` or `body`. The
            names are the library's own; symdef does not interpret them. Empty when none.
        family: The family name a renderer resolves the font by. Empty at construction means the
            same as `name`, so it is never empty. `measure_font` reads it from the face.
        text_block: How `slot_lines` sets a text block: "cap" or "grid" (D95).
    """

    name: str
    units_per_em: float
    cap_height: float
    ascent: float
    descent: float
    advances: Mapping[Weight, Mapping[str, float]]
    default_advance: Mapping[Weight, float]
    heights: Mapping[str, float] = field(default_factory=dict)
    family: str = ""
    text_block: str = "cap"

    def __post_init__(self) -> None:
        """Copy the mappings read-only; each text weight needs an advance table and a default."""
        if not self.family:
            object.__setattr__(self, "family", self.name)
        for what, given in (
            ("advance table", self.advances),
            ("default advance", self.default_advance),
        ):
            missing = [w.name for w in TEXT_WEIGHTS if w not in given]
            if missing:
                msg = f"font {self.name!r} has no {what} for {', '.join(missing)}; add one each"
                raise InvalidValueError(msg)
        tables = {w: MappingProxyType(dict(self.advances[w])) for w in TEXT_WEIGHTS}
        object.__setattr__(self, "advances", MappingProxyType(tables))
        defaults = {w: self.default_advance[w] for w in TEXT_WEIGHTS}
        object.__setattr__(self, "default_advance", MappingProxyType(defaults))
        object.__setattr__(self, "heights", MappingProxyType(dict(self.heights)))


def text_width(
    font: FontMetrics | None, text: str, height: float, weight: Weight = Weight.NORMAL
) -> float:
    """Return the width of a text in module units when set at `height` (one em).

    With a font it is the sum of the advances of the weight's table, in ems, times `height`. With
    no font it is 0.6 em per character.
    """
    if font is None:
        return DEFAULT_ADVANCE_EM * height * len(text)
    table = font.advances[weight]
    total = sum(table.get(char, font.default_advance[weight]) for char in text)
    return total / font.units_per_em * height


def cap_height(font: FontMetrics | None, height: float) -> float:
    """Return the height of a capital in module units when the text is set at `height`."""
    if font is None:
        return DEFAULT_CAP_EM * height
    return font.cap_height / font.units_per_em * height


def text_footprint(
    font: FontMetrics | None, text: str, cap_height_mm: float, grid: Grid, *, turn: bool = False
) -> tuple[int, int]:
    """Return the footprint of a text of one or more lines in whole divisions, as (width, height).

    The text is set so its capital is `cap_height_mm` tall. Upright it is its widest line by the
    block height, each rounded up. The block height follows the font's `text_block` rule: by "cap"
    one em box plus `LINE_PITCH` cap heights for each further line, by "grid" a whole row of
    divisions for each line. With `turn`, a turned slot's text that reads bottom-up, the two are
    exchanged: thickness by reading length, the `box` a `turn = true` slot declares.
    """
    em = em_height(font, cap_height_mm / grid.module_mm)
    lines = text.split("\n")
    if font is not None and font.text_block == "grid":
        height = len(lines) * ceil_divisions(grid, em)
    else:
        height = ceil_divisions(grid, em + (len(lines) - 1) * LINE_PITCH * cap_height(font, em))
    size = (ceil_divisions(grid, max(text_width(font, line, em) for line in lines)), height)
    return (size[1], size[0]) if turn else size


def em_height(font: FontMetrics | None, cap: float) -> float:
    """Return the text height whose capital is `cap` tall: the exact inverse of `cap_height`."""
    if font is None:
        return cap / DEFAULT_CAP_EM
    return cap * font.units_per_em / font.cap_height


def text_divisions(grid: Grid, font: FontMetrics | None, cap_height_mm: float) -> int:
    """Return the em box of a text whose capital is `cap_height_mm` tall, in whole grid divisions.

    It measures the em box, the line a text occupies, not the ink of its capitals.
    """
    return ceil_divisions(grid, em_height(font, cap_height_mm / grid.module_mm))
