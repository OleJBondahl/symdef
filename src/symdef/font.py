"""Font metrics as library data, and the width of a text measured with them."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from symdef.errors import InvalidValueError
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
        advances: One table per `Weight`: the advance width of each character, in font units.
        default_advance: The advance of a character a table does not list.
    """

    name: str
    units_per_em: float
    cap_height: float
    ascent: float
    descent: float
    advances: Mapping[Weight, Mapping[str, float]]
    default_advance: float

    def __post_init__(self) -> None:
        """Copy `advances` into read-only mappings; every `Weight` needs a table."""
        missing = [w.name for w in Weight if w not in self.advances]
        if missing:
            msg = f"font {self.name!r} has no advance table for {', '.join(missing)}; add one each"
            raise InvalidValueError(msg)
        tables = {w: MappingProxyType(dict(self.advances[w])) for w in Weight}
        object.__setattr__(self, "advances", MappingProxyType(tables))


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
    total = sum(table.get(char, font.default_advance) for char in text)
    return total / font.units_per_em * height


def cap_height(font: FontMetrics | None, height: float) -> float:
    """Return the height of a capital in module units when the text is set at `height`."""
    if font is None:
        return DEFAULT_CAP_EM * height
    return font.cap_height / font.units_per_em * height
