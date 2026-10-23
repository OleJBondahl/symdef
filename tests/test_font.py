"""Font metrics as library data: text width, text boxes and the bundle and TOML shapes (D73)."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from symdef.boxes import body_box, keepout_box
from symdef.errors import InvalidValueError, LibraryError
from symdef.files import load_bundle, load_library
from symdef.font import FontMetrics, cap_height, em_height, text_width
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


OVERFLOWING = """schema = 1
name = "Boxed"
kind = "qualifier"
status = "unverified"
reference = { standard = "IEC 60617", number = "S99999" }
anchors = [{ id = "link", at = [0, 0], dir = "E" }]
elements = [
  { line = [[0, 0], [2, 0]] },
  { text = "BBBBBBBBBB", at = [1, 0], height = 1 },
]
"""


def test_load_library_rejects_a_fixed_text_that_outgrows_its_body(tmp_path):
    shutil.copytree(GUIDE, tmp_path / "lib")
    toml = tmp_path / "lib" / "library.toml"
    toml.write_text(
        toml.read_text(encoding="utf-8") + "\n" + CONFIG.split("[font]")[1].join(["[font]", ""]),
        encoding="utf-8",
    )
    load_library(tmp_path / "lib")
    (tmp_path / "lib" / "symbols" / "S99999.toml").write_text(OVERFLOWING, encoding="utf-8")
    with pytest.raises(LibraryError) as raised:
        load_library(tmp_path / "lib")
    (found,) = raised.value.findings
    assert found.rule == "text-outside-body"
    assert "symbol S99999" in found.message
    assert "'BBBBBBBBBB'" in found.message
    assert "mm; shorten the text" in found.message


HEIGHTS = "\n[font.heights]\nsmallest = 1.8\nbody = 2.5\nheading_2 = 3.5\n"


def test_font_heights_are_read_frozen_and_empty_by_default():
    config, findings = parse_config(CONFIG + HEIGHTS)
    assert findings == ()
    assert config is not None
    assert config.font is not None
    assert dict(config.font.heights) == {"smallest": 1.8, "body": 2.5, "heading_2": 3.5}
    with pytest.raises(TypeError):
        config.font.heights["body"] = 1.0  # ty: ignore[invalid-assignment]  # frozen on purpose
    assert FONT.heights == {}


def test_font_heights_round_trip_through_the_bundle(tmp_path):
    shutil.copytree(GUIDE, tmp_path / "lib")
    toml = tmp_path / "lib" / "library.toml"
    toml.write_text(
        toml.read_text(encoding="utf-8") + "\n[font]" + CONFIG.split("[font]")[1] + HEIGHTS,
        encoding="utf-8",
    )
    loaded = load_library(tmp_path / "lib")
    assert loaded.font is not None
    assert loaded.font.heights["body"] == 2.5
    bundle = tmp_path / "bundle.json"
    bundle.write_text(to_json(bundle_to_data(loaded)), encoding="utf-8")
    assert load_bundle(bundle).font == loaded.font


def test_a_font_height_must_be_a_positive_number():
    _, findings = parse_config(CONFIG + "\n[font.heights]\nbody = 0\n")
    assert findings != ()


def test_the_literal_font_family_defaults_to_the_name_and_may_be_given():
    config, _ = parse_config(CONFIG)
    assert config is not None
    assert config.font is not None
    assert config.font.family == "Planted"
    config, findings = parse_config(
        CONFIG.replace('name = "Planted"', 'name = "Planted"\nfamily = "Fam"')
    )
    assert findings == ()
    assert config is not None
    assert config.font is not None
    assert (config.font.name, config.font.family) == ("Planted", "Fam")


def test_a_bundle_round_trips_the_font_family():
    font = replace(FONT, family="Fam")
    data = json.loads(to_json(bundle_to_data(library(font))))
    assert data["font"]["family"] == "Fam"
    assert validate_bundle(data) == ()
    loaded = library_from_bundle(data).font
    assert loaded is not None
    assert loaded.family == "Fam"


def test_em_height_inverts_cap_height():
    for font in (FONT, None):
        for cap in (0.5, 1.8, 2.5, 7.0):
            assert cap_height(font, em_height(font, cap)) == pytest.approx(cap, abs=1e-9)


def test_em_height_of_a_known_font():
    real = FontMetrics(
        name="Known",
        units_per_em=2048,
        cap_height=1493,
        ascent=1900,
        descent=500,
        advances={Weight.NORMAL: {}, Weight.THICK: {}},
        default_advance=1000,
    )
    assert em_height(real, 1.8) == pytest.approx(2.469, abs=1e-3)
    assert em_height(None, 0.72) == pytest.approx(1.0)
