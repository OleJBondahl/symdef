"""Font metrics as library data, and the width of a text measured with them."""

from collections.abc import Mapping
from dataclasses import dataclass

from symdef.geometry import Weight

# What a text measures when a library declares no font: 0.6 em per character, cap height 0.72 em.
DEFAULT_ADVANCE_EM = 0.6
DEFAULT_CAP_EM = 0.72


@dataclass(frozen=True, slots=True)
class FontMetrics:
    """The measures of one font, in the font's own units; `units_per_em` is one em.

    Attributes:
        name: The font's name, for the record; it changes no measure.
        units_per_em: How many font units make one em, the text height.
        cap_height: Height of a capital letter above the baseline, in font units.
        ascent: Height of the tallest glyph above the baseline, in font units.
        descent: Depth of the lowest glyph below the baseline, in font units.
        advances: The advance width of each character, in font units.
        default_advance: The advance of a character `advances` does not list.
        thick_factor: What an advance is multiplied by for `Weight.THICK`; 1 means no change.
    """

    name: str
    units_per_em: float
    cap_height: float
    ascent: float
    descent: float
    advances: Mapping[str, float]
    default_advance: float
    thick_factor: float = 1.0


def text_width(
    font: FontMetrics | None, text: str, height: float, weight: Weight = Weight.NORMAL
) -> float:
    """Return the width of a text in module units when set at `height` (one em).

    With a font it is the sum of the advances, in ems, times `height`, times the font's
    `thick_factor` for a thick weight. With no font it is 0.6 em per character.
    """
    if font is None:
        return DEFAULT_ADVANCE_EM * height * len(text)
    total = sum(font.advances.get(char, font.default_advance) for char in text)
    scale = font.thick_factor if weight is Weight.THICK else 1.0
    return total / font.units_per_em * height * scale


def cap_height(font: FontMetrics | None, height: float) -> float:
    """Return the height of a capital in module units when the text is set at `height`."""
    if font is None:
        return DEFAULT_CAP_EM * height
    return font.cap_height / font.units_per_em * height
