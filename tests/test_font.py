"""Font metrics as library data: text width, text boxes and the bundle and TOML shapes (D73)."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from symdef.boxes import body_box, keepout_box
from symdef.errors import InvalidValueError
from symdef.files import load_bundle, load_library
from symdef.font import FontMetrics, cap_height, text_width
from symdef.geometry import Box, Direction, Point, Text, Weight
from symdef.load import library_from_bundle, parse_config, validate_bundle
from symdef.model import Library, Reference, Slot, Status, Symbol, SymbolKind
from symdef.serialize import bundle_to_data, to_json

GUIDE = Path(__file__).resolve().parent / "fixtures" / "guide"

# A planted three-glyph table per weight: regular "A" is 500 units, "B" 700, "i" 250; bold sets
# each glyph by its own advance, not by a factor; anything else 600.
REGULAR = {"A": 500, "B": 700, "i": 250}
BOLD = {"A": 560, "B": 810, "i": 300}
FONT = FontMetrics(
    name="Planted",
    units_per_em=1000,
    cap_height=700,
    ascent=900,
    descent=200,
    advances={Weight.NORMAL: REGULAR, Weight.THICK: BOLD},
    default_advance=600,
)


def symbol(content="Bi", slots=()):
    return Symbol(
        "t",
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", "1"),
        (Text(content, Point(0, 0), 2),),
        slots=tuple(slots),
    )


def test_width_is_the_sum_of_the_advances_in_ems_times_the_height():
    assert text_width(FONT, "ABi", 2) == pytest.approx(2.9)
    assert text_width(FONT, "B", 1) == pytest.approx(0.7)


def test_a_missing_character_takes_the_default_advance():
    assert text_width(FONT, "AZ", 1) == pytest.approx(1.1)


def test_a_thick_weight_reads_its_own_table_glyph_by_glyph():
    assert text_width(FONT, "AB", 1, Weight.THICK) == pytest.approx(1.37)
    assert text_width(FONT, "i", 1, Weight.THICK) == pytest.approx(0.3)
    ratios = {c: BOLD[c] / REGULAR[c] for c in REGULAR}
    assert len(set(ratios.values())) == len(ratios)  # no single factor makes bold of regular


def test_a_font_needs_a_table_for_every_weight():
    with pytest.raises(InvalidValueError, match="no advance table for THICK"):
        replace(FONT, advances={Weight.NORMAL: REGULAR})


def test_no_font_measures_six_tenths_of_the_height_per_character():
    assert text_width(None, "abc", 2) == 0.6 * 2 * 3
    assert text_width(None, "", 2) == 0


def test_cap_height_follows_the_font_or_its_default():
    assert cap_height(FONT, 2) == pytest.approx(1.4)
    assert cap_height(None, 2) == 0.72 * 2


def test_body_box_measures_text_with_the_font_and_without_it_as_before():
    assert body_box(symbol()) == Box(Point(-1.2, -1), Point(1.2, 1))
    measured = body_box(symbol(), FONT)
    assert (measured.min.x, measured.max.x) == pytest.approx((-0.95, 0.95))


def test_keepout_box_passes_the_font_to_the_body():
    slot = Slot("tag", Point(5, 0), Direction.E, (1, 1))
    assert keepout_box(symbol(slots=[slot]), FONT).min.x == pytest.approx(-0.95)
    assert keepout_box(symbol(slots=[slot])).min.x == -1.2


def library(font):
    return Library("IEC 60617", "IEC 60617", "", {"1": symbol()}, font=font)


def test_a_bundle_round_trips_its_font():
    data = json.loads(to_json(bundle_to_data(library(FONT))))
    assert data["font"]["advances"] == {"normal": REGULAR, "thick": BOLD}
    assert validate_bundle(data) == ()
    assert library_from_bundle(data).font == FONT


def test_a_library_without_a_font_has_no_font_key_and_no_font():
    data = bundle_to_data(library(None))
    assert "font" not in data
    assert library_from_bundle(json.loads(to_json(data))).font is None


def test_a_bad_font_in_a_bundle_is_reported():
    data = json.loads(to_json(bundle_to_data(library(FONT))))
    data["font"]["advances"]["normal"]["AB"] = 1
    del data["font"]["advances"]["thick"]
    data["font"]["ascent"] = 0
    del data["font"]["descent"]
    messages = sorted(f.message for f in validate_bundle(data))
    assert messages == [
        "missing required key 'descent'",
        "missing required key 'thick'",
        "must be a single character",
        "must be above zero",
    ]


CONFIG = """
standard = "S"
title = "T"
number_pattern = '^S$'

[font]
name = "Planted"
units_per_em = 1000
cap_height = 700
ascent = 900
descent = 200
default_advance = 600

[font.advances.normal]
A = 500
B = 700
i = 250

[font.advances.thick]
A = 560
B = 810
i = 300
"""


def test_library_toml_declares_the_font():
    config, findings = parse_config(CONFIG)
    assert findings == ()
    assert config is not None
    assert config.font == FONT


def test_library_toml_without_a_font_has_none():
    config, _ = parse_config(CONFIG.split("[font]")[0])
    assert config is not None
    assert config.font is None


def test_library_toml_rejects_a_bad_font_and_an_unknown_key():
    _, findings = parse_config(CONFIG.replace("A = 500", "AB = 500").replace("ascent", "up"))
    assert sorted(f.message for f in findings) == [
        "missing required key 'ascent'",
        "must be a single character",
        "unknown key 'up'",
    ]


def test_load_library_carries_the_font_into_the_library_and_its_bundle(tmp_path):
    shutil.copytree(GUIDE, tmp_path / "lib")
    toml = tmp_path / "lib" / "library.toml"
    toml.write_text(
        toml.read_text(encoding="utf-8") + "\n" + CONFIG.split("[font]")[1].join(["[font]", ""]),
        encoding="utf-8",
    )
    loaded = load_library(tmp_path / "lib")
    assert loaded.font == FONT
    bundle = tmp_path / "bundle.json"
    bundle.write_text(to_json(bundle_to_data(loaded)), encoding="utf-8")
    assert load_bundle(bundle).font == FONT
