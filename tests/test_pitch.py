"""The two wire pitches of `[grid]`: a standard, a fine one that divides it, no third (D86)."""

import json
from pathlib import Path

import pytest
from neutral_font import NEUTRAL_FONT
from test_build_load import GUIDE

from symdef.errors import InvalidValueError, LibraryError
from symdef.files import load_library
from symdef.load import library_from_bundle, parse_config, validate_bundle
from symdef.model import Library
from symdef.serialize import bundle_to_data, to_json
from symdef.units import DEFAULT_GRID, Grid


def grid_config(*lines):
    """Return the guide config text with a `[grid]` table made of `lines`."""
    base = (GUIDE / "library.toml").read_text(encoding="utf-8")
    return base + "\n[grid]\nmodule_mm = 2.5\ndivisions_per_module = 8\n" + "\n".join(lines) + "\n"


def messages(*lines):
    config, findings = parse_config(grid_config(*lines))
    return config, [f.message for f in findings]


def repo(tmp_path: Path, *lines, port_x=0.5) -> Path:
    """Copy the junction symbol with its port moved to `port_x`, under a config with `lines`."""
    root = tmp_path / "repo"
    (root / "symbols").mkdir(parents=True)
    (root / "library.toml").write_text(grid_config(*lines), encoding="utf-8")
    text = (GUIDE / "symbols" / "connection-point.toml").read_text(encoding="utf-8")
    text = text.replace('{ id = "n", at = [0, 0]', f'{{ id = "n", at = [{port_x}, 0]')
    (root / "symbols" / "connection-point.toml").write_text(text, encoding="utf-8")
    return root


def test_the_default_grid_has_pitches_8_and_4():
    assert (DEFAULT_GRID.wire_pitch, DEFAULT_GRID.wire_pitch_fine) == (8, 4)


def test_a_library_names_both_pitches():
    config, found = messages("wire_pitch = 16", "wire_pitch_fine = 8")
    assert found == []
    assert (config.grid.wire_pitch, config.grid.wire_pitch_fine) == (16, 8)


def test_a_third_pitch_is_refused():
    config, found = messages("wire_pitch = 8", "wire_pitch_fine = 4", "wire_pitch_coarse = 16")
    assert config is None
    assert found == ["unknown key 'wire_pitch_coarse'"]


@pytest.mark.parametrize(("standard", "fine"), [(8, 3), (8, 16), (6, 4)])
def test_a_fine_pitch_that_does_not_divide_the_standard_one_is_refused(standard, fine):
    config, found = messages(f"wire_pitch = {standard}", f"wire_pitch_fine = {fine}")
    assert config is None
    assert any("does not divide wire_pitch" in m for m in found)


def test_a_pitch_must_be_a_whole_number_above_zero():
    assert messages("wire_pitch = 0")[0] is None
    assert messages("wire_pitch_fine = 2.5")[0] is None
    with pytest.raises(InvalidValueError, match="wire_pitch"):
        Grid(wire_pitch=0)


def test_a_port_off_the_standard_pitch_is_refused_at_load(tmp_path):
    with pytest.raises(LibraryError) as raised:
        load_library(repo(tmp_path, "wire_pitch = 8", "wire_pitch_fine = 4"))
    (finding,) = [f for f in raised.value.findings if f.rule == "port-off-wiring-grid"]
    assert "wire pitch of 8 divisions" in finding.message
    assert "x 0.5" in finding.message


def test_the_same_port_loads_when_the_standard_pitch_is_half_a_module(tmp_path):
    library = load_library(repo(tmp_path, "wire_pitch = 4", "wire_pitch_fine = 2"))
    assert isinstance(library, Library)
    assert library.grid.wire_pitch == 4


def test_a_port_on_the_pitch_loads(tmp_path):
    assert len(load_library(repo(tmp_path, "wire_pitch = 8", port_x=1))) == 1


def test_the_guide_library_loads_on_its_default_pitch():
    assert load_library(GUIDE).grid == DEFAULT_GRID


def test_the_pitches_round_trip_through_the_bundle():
    library = Library("S", "S", "", {}, grid=Grid(2.5, 8, 16, 8), font=NEUTRAL_FONT)
    data = json.loads(to_json(bundle_to_data(library)))
    assert data["grid"]["wire_pitch"] == 16
    assert validate_bundle(data) == ()
    assert library_from_bundle(data).grid == library.grid
