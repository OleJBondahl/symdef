"""A library has a font: one without is refused at load, naming the key (D124)."""

import pytest
from neutral_font import NEUTRAL_FONT

from symdef import Library, LibraryError, load_library
from symdef.load import parse_config, validate_bundle
from symdef.serialize import bundle_to_data

HEAD = "standard = 'S'\ntitle = 'T'\nnumber_pattern = '^S$'\nport_format = '{k}.{port}'\n"


def test_a_library_toml_without_a_font_is_refused_with_the_key_and_the_fix():
    config, findings = parse_config(HEAD)
    assert config is None
    (found,) = findings
    assert "missing required key 'font'" in found.message
    assert "[font]" in found.message


def test_a_loaded_directory_without_a_font_fails_with_that_finding(tmp_path):
    (tmp_path / "library.toml").write_text(HEAD)
    (tmp_path / "symbols").mkdir()
    with pytest.raises(LibraryError) as raised:
        load_library(tmp_path)
    assert any("missing required key 'font'" in f.message for f in raised.value.findings)


def test_a_bundle_without_a_font_object_is_invalid():
    data = bundle_to_data(Library("S", "S", "", {}, font=NEUTRAL_FONT))
    assert validate_bundle(data) == ()
    del data["font"]
    (found,) = validate_bundle(data)
    assert "font" in found.message


def test_a_library_cannot_be_built_without_a_font():
    with pytest.raises(TypeError, match="font"):
        Library("S", "S", "", {})  # ty: ignore[missing-argument]  # the point of the test
