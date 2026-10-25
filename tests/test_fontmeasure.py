"""`measure_font` against an independent oracle, and the `[font]` files form (D87)."""

import json
import re
import shutil
from io import BytesIO
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

import symdef
from symdef.errors import InvalidValueError, LibraryError
from symdef.files import load_library, write_build
from symdef.font import text_width
from symdef.fontmeasure import measure_font
from symdef.geometry import Weight
from symdef.load import parse_config

TESTS = Path(__file__).resolve().parent
GUIDE = TESTS / "fixtures" / "guide"
DATA = TESTS / "data" / "dejavu"
REGULAR = (DATA / "DejaVuSansCondensed.ttf").read_bytes()
BOLD = (DATA / "DejaVuSansCondensed-Bold.ttf").read_bytes()
EXPECTED = json.loads((DATA / "expected.json").read_text(encoding="utf-8"))
FAMILY = "DejaVu Sans"  # name ID 16 of the vendored face; ID 1 is the name
BUNDLE = "src/iec60617/bundle.json"
FILES = '[font]\nname = "DejaVu Sans Condensed"\nfiles = { regular = "r.ttf", bold = "b.ttf" }\n'


def changed(data: bytes, edit) -> bytes:
    """The TTF bytes after `edit(font)` ran on the parsed font."""
    font = TTFont(BytesIO(data))
    edit(font)
    out = BytesIO()
    font.save(out)
    return out.getvalue()


def without_glyph(character: str):
    def edit(font):
        for table in font["cmap"].tables:
            table.cmap.pop(ord(character), None)

    return edit


class TestMeasure:
    def test_the_house_font_equals_the_oracle_field_by_field(self):
        metrics = measure_font(REGULAR, BOLD)
        for field in ("name", "units_per_em", "cap_height", "ascent", "descent"):
            assert getattr(metrics, field) == EXPECTED[field], field
        assert dict(metrics.advances[Weight.NORMAL]) == EXPECTED["advances"]["normal"]
        assert dict(metrics.advances[Weight.THICK]) == EXPECTED["advances"]["thick"]
        assert len(metrics.advances[Weight.NORMAL]) == len(metrics.advances[Weight.THICK]) == 197
        assert dict(metrics.default_advance) == {
            Weight.NORMAL: EXPECTED["default_advance"]["normal"],
            Weight.THICK: EXPECTED["default_advance"]["thick"],
        }
        assert dict(metrics.heights) == {}

    @pytest.mark.parametrize("character", ["H", "p"])
    def test_a_face_without_the_glyph_names_it(self, character):
        broken = changed(REGULAR, without_glyph(character))
        with pytest.raises(InvalidValueError, match=f"no glyph '{character}'"):
            measure_font(broken, BOLD)
        with pytest.raises(InvalidValueError, match=f"bold font has no glyph '{character}'"):
            measure_font(REGULAR, changed(BOLD, without_glyph(character)))

    def test_faces_with_other_units_per_em_are_refused(self):
        other = changed(BOLD, lambda font: setattr(font["head"], "unitsPerEm", 1000))
        with pytest.raises(InvalidValueError, match="2048 units per em and the bold font 1000"):
            measure_font(REGULAR, other)

    @pytest.mark.parametrize("pair", [(b"not a font", BOLD), (REGULAR, b""), (b"", b"")])
    def test_bytes_that_are_not_a_ttf_are_refused(self, pair):
        with pytest.raises(InvalidValueError, match="not a TrueType font"):
            measure_font(*pair)

    def test_an_unknown_glyph_is_wider_in_bold_by_each_faces_own_widest_advance(self):
        metrics = measure_font(REGULAR, BOLD)
        unknown = "\u2603"  # in neither table
        assert unknown not in metrics.advances[Weight.NORMAL]
        assert unknown not in metrics.advances[Weight.THICK]
        normal = text_width(metrics, unknown, 1)
        thick = text_width(metrics, unknown, 1, Weight.THICK)
        assert normal == max(metrics.advances[Weight.NORMAL].values()) / metrics.units_per_em
        assert thick == max(metrics.advances[Weight.THICK].values()) / metrics.units_per_em
        assert thick > normal

    def test_it_is_exported(self):
        assert symdef.measure_font is measure_font


def library(tmp_path, font_toml: str) -> Path:
    root = tmp_path / "lib"
    shutil.copytree(GUIDE, root)
    (root / "r.ttf").write_bytes(REGULAR)
    (root / "b.ttf").write_bytes(BOLD)
    toml = root / "library.toml"
    text = re.sub(
        r"\[font\].*?(?=\[vocabulary\])", "", toml.read_text(encoding="utf-8"), flags=re.DOTALL
    )
    toml.write_text(text + "\n" + font_toml, encoding="utf-8")
    return root


def literal_toml() -> str:
    """The `[font]` tables of the oracle, in the literal form."""
    head = (
        "".join(
            f"{key} = {EXPECTED[key]}\n"
            for key in ("units_per_em", "cap_height", "ascent", "descent")
        )
        + "\n[font.default_advance]\n"
        + "".join(f"{w} = {n}\n" for w, n in EXPECTED["default_advance"].items())
    )
    tables = "".join(
        f"\n[font.advances.{weight}]\n"
        + "".join(f"{json.dumps(c)} = {n}\n" for c, n in table.items())
        for weight, table in EXPECTED["advances"].items()
    )
    family = json.dumps(FAMILY)
    return f"[font]\nname = {json.dumps(EXPECTED['name'])}\nfamily = {family}\n{head}{tables}"


class TestFilesForm:
    def test_the_files_form_builds_the_same_bundle_as_the_literal_tables(self, tmp_path):
        files = library(tmp_path / "files", FILES)
        literal = library(tmp_path / "literal", literal_toml())
        write_build(load_library(files), files)
        write_build(load_library(literal), literal)
        bundle = (files / BUNDLE).read_bytes()
        assert bundle == (literal / BUNDLE).read_bytes()
        assert json.loads(bundle)["font"]["advances"]["normal"] == EXPECTED["advances"]["normal"]

    def test_the_name_in_library_toml_wins_over_the_name_in_the_ttf(self, tmp_path):
        root = library(tmp_path, FILES.replace("DejaVu Sans Condensed", "House"))
        font = load_library(root).font
        assert font is not None
        assert font.name == "House"
        assert font.cap_height == EXPECTED["cap_height"]

    def test_a_missing_file_is_a_schema_finding_at_the_font(self, tmp_path):
        root = library(tmp_path, FILES)
        (root / "b.ttf").unlink()
        with pytest.raises(LibraryError) as caught:
            load_library(root)
        (finding,) = caught.value.findings
        assert (finding.rule, finding.location) == ("schema", "/font/files")
        assert finding.message.startswith("library.toml: ")
        assert "b.ttf" in finding.message

    def test_a_file_that_is_not_a_ttf_is_a_schema_finding(self, tmp_path):
        root = library(tmp_path, FILES)
        (root / "r.ttf").write_bytes(b"nope")
        with pytest.raises(LibraryError, match="not a TrueType font"):
            load_library(root)

    def test_a_literal_library_still_loads_with_no_files(self, tmp_path):
        root = library(tmp_path, literal_toml())
        loaded = load_library(root)
        assert loaded.font is not None
        assert loaded.font.default_advance[Weight.THICK] == EXPECTED["default_advance"]["thick"]


MIXED = (
    "`{}` is not a key of the files form (`name`, `files`, `heights`, `text_block`); "
    "remove it, or drop `files` and give the measured tables"
)
HEAD = "standard = 'S'\ntitle = 'T'\nnumber_pattern = '^S$'\n"


class TestConfig:
    def test_files_parse_into_the_config_and_leave_the_font_empty(self):
        config, findings = parse_config(HEAD + FILES)
        assert findings == ()
        assert config is not None
        assert config.font_files == ("r.ttf", "b.ttf")
        assert config.font_name == "DejaVu Sans Condensed"

    def test_no_font_is_a_finding(self):
        config, findings = parse_config(HEAD)
        assert config is None
        assert [f.message for f in findings if "'font'" in f.message] != []

    def test_the_two_forms_cannot_be_mixed(self):
        text = HEAD + FILES + "units_per_em = 2048\n"
        _, findings = parse_config(text)
        assert [f.message for f in findings] == [MIXED.format("units_per_em")]

    def test_the_first_offending_key_is_the_one_named(self):
        _, findings = parse_config(HEAD + FILES + "ascent = 1\nunits_per_em = 2048\n")
        assert [f.message for f in findings] == [MIXED.format("ascent")]

    def test_a_measured_table_beside_files_names_the_table(self):
        _, findings = parse_config(HEAD + FILES + "[font.advances.normal]\n")
        assert [f.message for f in findings] == [MIXED.format("advances")]

    @pytest.mark.parametrize(
        "text", [FILES + "units_per_em = 2048\n", FILES + 'family = "X"\n', FILES + "[font.x]\n"]
    )
    def test_every_refusal_names_a_key_and_a_fix(self, text):
        (finding,) = parse_config(HEAD + text)[1]
        assert re.search(r"`\w+`", finding.message)
        assert re.search(r"\b(remove|drop|add)\b", finding.message)

    def test_files_need_both_faces(self):
        _, findings = parse_config(HEAD + FILES.replace(', bold = "b.ttf"', ""))
        assert [(f.location, f.message) for f in findings] == [
            ("/font/files", "missing required key 'bold'")
        ]

    def test_files_need_a_name(self):
        _, findings = parse_config(HEAD + FILES.replace('name = "DejaVu Sans Condensed"\n', ""))
        assert [f.message for f in findings] == ["missing required key 'name'"]


class TestFamily:
    def test_the_house_font_family_is_the_typographic_one(self):
        metrics = measure_font(REGULAR, BOLD)
        assert metrics.name == "DejaVu Sans Condensed"
        assert metrics.family == FAMILY

    def test_a_face_without_name_id_16_falls_back_to_id_1(self):
        def drop_16(font):
            font["name"].names = [n for n in font["name"].names if n.nameID != 16]

        assert measure_font(changed(REGULAR, drop_16), BOLD).family == "DejaVu Sans Condensed"

    def test_family_beside_files_is_refused(self):
        _, findings = parse_config(HEAD + FILES + 'family = "DejaVu Sans"\n')
        assert [f.message for f in findings] == [
            "`family` comes from the font file; remove it beside `files`"
        ]


HEIGHTS = "heights = { smallest = 1.8, body = 2.5, heading = 3.5, large = 5.0 }\n"
LITERAL_H = "smallest = 1.8\nbody = 2.5\nheading = 3.5\nlarge = 5.0\n"


class TestHeights:
    def test_heights_beside_files_parse_into_the_config(self):
        config, findings = parse_config(HEAD + FILES + HEIGHTS)
        assert findings == ()
        assert config is not None
        assert dict(config.font_heights) == {
            "smallest": 1.8,
            "body": 2.5,
            "heading": 3.5,
            "large": 5.0,
        }

    def test_no_heights_leaves_the_config_heights_empty(self):
        config, _ = parse_config(HEAD + FILES)
        assert config is not None
        assert dict(config.font_heights) == {}

    @pytest.mark.parametrize("bad", ["0", "-1", '"tall"'])
    def test_a_bad_height_is_a_finding_at_its_name(self, bad):
        _, findings = parse_config(HEAD + FILES + f"heights = {{ body = {bad} }}\n")
        assert [f.location for f in findings] == ["/font/heights/body"]

    def test_the_literal_form_locates_a_bad_height_the_same_way(self):
        text = HEAD + literal_toml() + "\n[font.heights]\nbody = 0\n"
        _, findings = parse_config(text)
        assert [f.location for f in findings] == ["/font/heights/body"]

    def test_the_files_form_carries_the_heights_on_the_font(self, tmp_path):
        root = library(tmp_path, FILES + HEIGHTS)
        font = load_library(root).font
        assert font is not None
        assert dict(font.heights) == {"smallest": 1.8, "body": 2.5, "heading": 3.5, "large": 5.0}
        assert font.name == "DejaVu Sans Condensed"
        assert dict(font.advances[Weight.NORMAL]) == EXPECTED["advances"]["normal"]

    def test_a_files_form_without_heights_has_none_and_no_bundle_key(self, tmp_path):
        root = library(tmp_path, FILES)
        loaded = load_library(root)
        assert loaded.font is not None
        assert dict(loaded.font.heights) == {}
        write_build(loaded, root)
        assert "heights" not in json.loads((root / BUNDLE).read_text())["font"]

    def test_the_bundle_reads_the_heights_back(self, tmp_path):
        root = library(tmp_path, FILES + HEIGHTS)
        write_build(load_library(root), root)
        font = json.loads((root / BUNDLE).read_text())["font"]
        assert font["heights"] == {"smallest": 1.8, "body": 2.5, "heading": 3.5, "large": 5.0}
        read = load_library(root).font
        assert read is not None
        assert dict(read.heights) == font["heights"]

    def test_files_and_literal_forms_with_heights_build_the_same_bundle(self, tmp_path):
        files = library(tmp_path / "files", FILES + HEIGHTS)
        literal = library(tmp_path / "literal", literal_toml() + "\n[font.heights]\n" + LITERAL_H)
        write_build(load_library(files), files)
        write_build(load_library(literal), literal)
        assert (files / BUNDLE).read_bytes() == (literal / BUNDLE).read_bytes()

    def test_with_settings_keeps_the_heights_of_a_files_form_font(self, tmp_path):
        base = load_library(library(tmp_path, FILES + HEIGHTS))
        again = base.with_settings(font=(REGULAR, BOLD))
        assert again.font is not None
        assert base.font is not None
        assert dict(again.font.heights) == dict(base.font.heights) != {}

    def test_family_beside_files_and_heights_is_the_only_finding(self):
        _, findings = parse_config(HEAD + FILES + HEIGHTS + 'family = "DejaVu Sans"\n')
        assert [f.message for f in findings] == [
            "`family` comes from the font file; remove it beside `files`"
        ]

    def test_heights_and_files_without_a_name_is_still_the_missing_key(self):
        text = FILES.replace('name = "DejaVu Sans Condensed"\n', "") + HEIGHTS
        _, findings = parse_config(HEAD + text)
        assert [f.message for f in findings] == ["missing required key 'name'"]
