"""Measure a regular and a bold TrueType face into `FontMetrics` (D87); the caller reads files."""

from io import BytesIO  # memory only: fontTools reads a file object, and this reads no file
from struct import error as struct_error
from typing import Any, cast

from fontTools.ttLib import TTFont, TTLibError

from symdef.errors import InvalidValueError
from symdef.font import FontMetrics
from symdef.geometry import TEXT_WEIGHTS

# ASCII, Latin-1 (without the C1 controls), and the dashes, ellipsis, euro and ohm signs
CODEPOINTS = (
    *range(0x20, 0x7F),
    *range(0xA0, 0x100),
    0x2013,
    0x2014,
    0x2026,
    0x20AC,
    0x2126,
    0x03A9,
)


def _open(data: bytes, face: str) -> TTFont:
    """Parse one face; bytes that are not a TrueType font are an `InvalidValueError`."""
    try:
        return TTFont(BytesIO(data))
    except (TTLibError, struct_error, AssertionError, EOFError) as error:
        message = f"the {face} font is not a TrueType font ({error}); pass the bytes of a .ttf file"
        raise InvalidValueError(message) from error


def _bounds(font: TTFont, character: str, face: str) -> tuple[int, int]:
    """Return the lowest and highest point of a glyph, or raise naming the missing glyph."""
    name = cast("Any", font.getBestCmap()).get(ord(character))
    if name is None:
        message = (
            f"the {face} font has no glyph {character!r}, which gives the cap height and the "
            f"descent; use a font that has it"
        )
        raise InvalidValueError(message)
    glyph = cast("Any", font["glyf"])[name]
    return glyph.yMin, glyph.yMax


def _advances(font: TTFont) -> dict[str, int]:
    """Return the advance of each covered code point in the face; an absent one is skipped."""
    cmap: Any = font.getBestCmap()
    hmtx: Any = font["hmtx"]
    return {chr(cp): hmtx[cmap[cp]][0] for cp in CODEPOINTS if cp in cmap}


def _units(regular: TTFont, bold: TTFont) -> int:
    """Return the units per em the two faces share, or raise."""
    one, other = (cast("Any", f["head"]).unitsPerEm for f in (regular, bold))
    if one != other:
        message = (
            f"the regular font has {one} units per em and the bold font {other}; "
            f"use two faces of the same family"
        )
        raise InvalidValueError(message)
    return one


def measure_font(regular: bytes, bold: bytes) -> FontMetrics:
    """Measure a regular and a bold TrueType face into font metrics.

    The normal advances come from the regular face, the thick ones from the bold face, each for
    ASCII, Latin-1 and a few symbols. The cap height is the top of the glyph `H`, the descent the
    depth of the glyph `p` and the ascent the OS/2 typographic ascender, all from the regular face.

    Args:
        regular: The bytes of the regular `.ttf` file.
        bold: The bytes of the bold `.ttf` file.

    Returns:
        The metrics: named by the regular face (name ID 1) and with its typographic family (name ID
        16, else ID 1) as `family`, with each face's largest advance as its default advance and no
        heights.

    Raises:
        InvalidValueError: If either argument is not a TrueType font, the faces differ in units
            per em, or a face has no glyph `H` or `p`.
    """
    faces = {"regular": _open(regular, "regular"), "bold": _open(bold, "bold")}
    for face, font in faces.items():
        _bounds(font, "H", face)
        _bounds(font, "p", face)
    normal, thick = (_advances(faces[face]) for face in ("regular", "bold"))
    names = cast("Any", faces["regular"]["name"])
    return FontMetrics(
        name=names.getDebugName(1) or "",
        family=names.getDebugName(16) or names.getDebugName(1) or "",
        units_per_em=_units(faces["regular"], faces["bold"]),
        cap_height=_bounds(faces["regular"], "H", "regular")[1],
        ascent=cast("Any", faces["regular"]["OS/2"]).sTypoAscender,
        descent=-_bounds(faces["regular"], "p", "regular")[0],
        advances=dict(zip(TEXT_WEIGHTS, (normal, thick), strict=True)),
        default_advance={
            w: max(table.values()) for w, table in zip(TEXT_WEIGHTS, (normal, thick), strict=True)
        },
    )
