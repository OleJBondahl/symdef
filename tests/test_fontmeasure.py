"""`measure_font` against an independent oracle, and the `[font]` files form (D87)."""

import json
import shutil
from io import BytesIO
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

import symdef
from symdef.errors import InvalidValueError, LibraryError
from symdef.files import load_library, write_build
from symdef.fontmeasure import measure_font
from symdef.geometry import Weight
from symdef.load import parse_config

TESTS = Path(__file__).resolve().parent
GUIDE = TESTS / "fixtures" / "guide"
DATA = TESTS / "data" / "dejavu"
REGULAR = (DATA / "DejaVuSansCondensed.ttf").read_bytes()
BOLD = (DATA / "DejaVuSansCondensed-Bold.ttf").read_bytes()
EXPECTED = json.loads((DATA / "expected.json").read_text(encoding="utf-8"))
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
        for field in ("name", "units_per_em", "cap_height", "ascent", "descent", "default_advance"):
            assert getattr(metrics, field) == EXPECTED[field], field
        assert dict(metrics.advances[Weight.NORMAL]) == EXPECTED["advances"]["normal"]
        assert dict(metrics.advances[Weight.THICK]) == EXPECTED["advances"]["thick"]
        assert len(metrics.advances[Weight.NORMAL]) == len(metrics.advances[Weight.THICK]) == 197
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

    def test_it_is_exported(self):
        assert symdef.measure_font is measure_font


def library(tmp_path, font_toml: str) -> Path:
    root = tmp_path / "lib"
    shutil.copytree(GUIDE, root)
    (root / "r.ttf").write_bytes(REGULAR)
    (root / "b.ttf").write_bytes(BOLD)
    toml = root / "library.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + "\n" + font_toml, encoding="utf-8")
    return root


def literal_toml() -> str:
    """The `[font]` tables of the oracle, in the literal form."""
    head = "".join(
        f"{key} = {EXPECTED[key]}\n"
        for key in ("units_per_em", "cap_height", "ascent", "descent", "default_advance")
    )
    tables = "".join(
        f"\n[font.advances.{weight}]\n"
        + "".join(f"{json.dumps(c)} = {n}\n" for c, n in table.items())
        for weight, table in EXPECTED["advances"].items()
    )
    return f"[font]\nname = {json.dumps(EXPECTED['name'])}\n{head}{tables}"


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
        assert loaded.font.default_advance == EXPECTED["default_advance"]


HEAD = "standard = 'S'\ntitle = 'T'\nnumber_pattern = '^S$'\n"


class TestConfig:
    def test_files_parse_into_the_config_and_leave_the_font_empty(self):
        config, findings = parse_config(HEAD + FILES)
        assert findings == ()
        assert config is not None
        assert config.font is None
        assert config.font_files == ("r.ttf", "b.ttf")
        assert config.font_name == "DejaVu Sans Condensed"

    def test_no_font_leaves_no_files(self):
        config, _ = parse_config(HEAD)
        assert config is not None
        assert (config.font_files, config.font_name) == (None, "")

    def test_the_two_forms_cannot_be_mixed(self):
        text = HEAD + FILES + "units_per_em = 2048\n"
        _, findings = parse_config(text)
        assert [f.message for f in findings] == [
            "give either the measured tables or `name` and `files`, not both"
        ]

    def test_files_need_both_faces(self):
        _, findings = parse_config(HEAD + FILES.replace(', bold = "b.ttf"', ""))
        assert [(f.location, f.message) for f in findings] == [
            ("/font/files", "missing required key 'bold'")
        ]

    def test_files_need_a_name(self):
        _, findings = parse_config(HEAD + FILES.replace('name = "DejaVu Sans Condensed"\n', ""))
        assert [f.message for f in findings] == ["missing required key 'name'"]
