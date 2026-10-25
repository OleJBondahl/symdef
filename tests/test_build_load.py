"""`load_library`: the only place the resolver's inputs are read from disk."""

import shutil
from pathlib import Path

import pytest
from neutral_font import NEUTRAL_FONT_TOML
from words import WORDS

import symdef
from symdef.errors import LibraryError, UnknownSymbolError
from symdef.files import load_library
from symdef.model import Library

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GUIDE = FIXTURES / "guide"
BROKEN = FIXTURES / "broken"

CONFIG = (
    'standard = "Example set"\ntitle = "t"\nnumber_pattern = \'^[a-z][a-z0-9]*(-[a-z0-9]+)*$\'\n'
    'port_format = "{k}.{port}"\n' + WORDS + NEUTRAL_FONT_TOML
)


def broken_library(rule_id: str, tmp_path: Path) -> Path:
    """Copy a broken fixture and the default config into a data repo layout."""
    shutil.copytree(BROKEN / rule_id, tmp_path / "repo")
    shutil.copy(BROKEN / "library.toml", tmp_path / "repo" / "library.toml")
    return tmp_path / "repo"


def data_repo(tmp_path: Path, config: str | None = None) -> Path:
    root = tmp_path / "repo"
    (root / "symbols").mkdir(parents=True)
    if config is not None:
        (root / "library.toml").write_text(config, encoding="utf-8")
    return root


class TestGuideLibrary:
    def test_loads_the_six_guide_symbols(self):
        library = load_library(GUIDE)
        assert isinstance(library, Library)
        assert len(library) == 6
        assert [s.reference.number for s in library] == [
            "change-over-contact",
            "connection-point",
            "make-contact",
            "operated-by-pushing",
            "push-button",
            "relay-coil",
        ]

    def test_carries_the_config(self):
        library = load_library(GUIDE)
        assert (library.standard, library.title, library.number_pattern) == (
            "Example set",
            "Example set symbols",
            r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
        )

    def test_get_returns_the_flattened_composite(self):
        push = load_library(GUIDE).get("push-button")
        assert [p.id for p in push.ports] == ["in", "out"]
        assert len(push.elements) == 6

    def test_get_of_an_unknown_number_raises(self):
        with pytest.raises(UnknownSymbolError):
            load_library(GUIDE).get("sym-missing")

    def test_is_exported_by_the_package(self):
        assert symdef.load_library is load_library


class TestFailures:
    def test_a_broken_fixture_raises_library_error_with_its_findings(self, tmp_path):
        with pytest.raises(LibraryError) as raised:
            load_library(broken_library("part-unknown", tmp_path))
        (finding,) = raised.value.findings
        assert (finding.rule, finding.location) == ("part-unknown", "/parts/0/use")
        assert finding.message.startswith("sym-a.toml: ")
        assert "part-unknown" in str(raised.value)

    def test_findings_of_all_files_are_listed_in_name_order(self, tmp_path):
        with pytest.raises(LibraryError) as raised:
            load_library(broken_library("part-cycle", tmp_path))
        assert [f.message.split(":")[0] for f in raised.value.findings] == [
            "sym-a.toml",
            "sym-j.toml",
        ]

    def test_findings_of_every_kind_are_collected(self, tmp_path):
        root = data_repo(tmp_path, CONFIG)
        metadata = (BROKEN / "metadata" / "symbols" / "sym-a.toml").read_text(encoding="utf-8")
        (root / "symbols" / "sym-a.toml").write_text(metadata, encoding="utf-8")
        (root / "symbols" / "sym-b.toml").write_text('schema = 1\nkind = "x"\n', encoding="utf-8")
        with pytest.raises(LibraryError) as raised:
            load_library(root)
        assert raised.value.findings[0].rule == "metadata"
        assert raised.value.findings[0].message.startswith("sym-a.toml: ")
        assert {f.rule for f in raised.value.findings} == {"metadata", "schema"}
        assert {f.message.split(":")[0] for f in raised.value.findings} == {
            "sym-a.toml",
            "sym-b.toml",
        }

    def test_a_missing_library_toml_is_a_schema_finding(self, tmp_path):
        with pytest.raises(LibraryError) as raised:
            load_library(data_repo(tmp_path))
        (finding,) = raised.value.findings
        assert (finding.rule, finding.location) == ("schema", "library.toml")
        assert finding.message.startswith("library.toml: ")

    def test_a_missing_symbols_directory_is_a_schema_finding(self, tmp_path):
        root = tmp_path / "repo"
        root.mkdir()
        (root / "library.toml").write_text(CONFIG, encoding="utf-8")
        with pytest.raises(LibraryError) as raised:
            load_library(root)
        (finding,) = raised.value.findings
        assert (finding.rule, finding.location) == ("schema", "symbols")

    def test_a_bad_library_toml_is_reported_and_the_symbols_are_still_read(self, tmp_path):
        root = data_repo(tmp_path, 'standard = "X"\n')
        (root / "symbols" / "sym-a.toml").write_text("= broken", encoding="utf-8")
        with pytest.raises(LibraryError) as raised:
            load_library(root)
        assert [f.message.split(":")[0] for f in raised.value.findings] == [
            "library.toml",
            "library.toml",
            "library.toml",
            "library.toml",
            "sym-a.toml",
        ]

    def test_invalid_toml_in_a_symbol_file_is_a_schema_finding(self, tmp_path):
        root = data_repo(tmp_path, CONFIG)
        (root / "symbols" / "sym-a.toml").write_text("= broken", encoding="utf-8")
        shutil.copy(GUIDE / "symbols" / "make-contact.toml", root / "symbols" / "make-contact.toml")
        with pytest.raises(LibraryError) as raised:
            load_library(root)
        (finding,) = raised.value.findings
        assert (finding.rule, finding.message.split(":")[0]) == ("schema", "sym-a.toml")

    def test_a_file_that_is_not_utf8_is_a_schema_finding(self, tmp_path):
        root = data_repo(tmp_path, CONFIG)
        (root / "symbols" / "sym-a.toml").write_bytes(b"name = '\xff\xfe'")
        with pytest.raises(LibraryError) as raised:
            load_library(root)
        (finding,) = raised.value.findings
        assert (finding.rule, finding.location) == ("schema", "sym-a.toml")

    def test_a_directory_named_like_a_symbol_file_is_a_schema_finding(self, tmp_path):
        root = data_repo(tmp_path, CONFIG)
        (root / "symbols" / "sym-a.toml").mkdir()
        with pytest.raises(LibraryError) as raised:
            load_library(root)
        assert [f.rule for f in raised.value.findings] == ["schema"]


class TestEdgeCases:
    def test_an_empty_symbols_directory_gives_an_empty_library(self, tmp_path):
        assert len(load_library(data_repo(tmp_path, CONFIG))) == 0

    def test_files_other_than_toml_are_ignored(self, tmp_path):
        root = data_repo(tmp_path, CONFIG)
        (root / "symbols" / "notes.txt").write_text("not a symbol", encoding="utf-8")
        assert len(load_library(root)) == 0

    def test_crlf_files_load(self, tmp_path):
        root = data_repo(tmp_path, CONFIG)
        text = (GUIDE / "symbols" / "make-contact.toml").read_bytes().replace(b"\n", b"\r\n")
        (root / "symbols" / "make-contact.toml").write_bytes(text)
        assert len(load_library(root)) == 1
