"""The library's grid: `[grid]` in `library.toml`, the bundle key and the lint rule (D73)."""

import json
import re

import pytest
from test_font import CONFIG

from symdef.geometry import Line, Point
from symdef.lint import lint
from symdef.lint.geometry import off_drawing_grid
from symdef.load import library_from_bundle, parse_config, validate_bundle
from symdef.model import Library, Reference, Status, Symbol, SymbolKind
from symdef.project import _lint_findings
from symdef.serialize import bundle_to_data, to_json
from symdef.units import DEFAULT_GRID, Grid, on_grid, snap, to_divisions

COARSE = Grid(module_mm=5, divisions_per_module=4)


def symbol(x):
    return Symbol(
        "t",
        SymbolKind.ELEMENT,
        Status.UNVERIFIED,
        Reference("X", "1"),
        (Line(Point(0, 0), Point(x, 0)),),
    )


def test_the_default_grid_is_todays():
    assert Grid(2.5, 8) == DEFAULT_GRID
    assert DEFAULT_GRID.division == 0.125
    assert COARSE.division == 0.25


def config(table):
    config, findings = parse_config(CONFIG.split("[font]")[0] + table)
    return config, sorted(f.message for f in findings)


def test_library_toml_declares_the_grid():
    parsed, findings = config("[grid]\nmodule_mm = 5\ndivisions_per_module = 4\n")
    assert findings == []
    assert parsed.grid == COARSE


def test_library_toml_without_a_grid_has_the_default():
    parsed, _ = config("")
    assert parsed.grid == DEFAULT_GRID


@pytest.mark.parametrize("divisions", [0, 3, -4, 2.5])
def test_divisions_must_be_a_power_of_two(divisions):
    _, findings = config(f"[grid]\nmodule_mm = 5\ndivisions_per_module = {divisions}\n")
    assert findings
    assert all(m.startswith("must be") or "power of two" in m for m in findings)


def test_a_grid_needs_both_keys_and_no_others():
    _, findings = config("[grid]\nmodule_mm = 5\nextra = 1\n")
    assert findings == ["missing required key 'divisions_per_module'", "unknown key 'extra'"]


def library(grid):
    return Library("S", "S", "", {"1": symbol(1)}, grid=grid)


def test_a_bundle_round_trips_a_non_default_grid():
    data = json.loads(to_json(bundle_to_data(library(COARSE))))
    assert data["grid"] == {"module_mm": 5, "divisions_per_module": 4}
    assert validate_bundle(data) == ()
    assert library_from_bundle(data).grid == COARSE


def test_a_default_grid_is_not_written_and_reads_back_as_the_default():
    data = bundle_to_data(library(DEFAULT_GRID))
    assert "grid" not in data
    assert library_from_bundle(json.loads(to_json(data))).grid == DEFAULT_GRID


def test_lint_checks_against_the_librarys_own_grid():
    assert off_drawing_grid(symbol(0.125)) == ()
    (found,) = off_drawing_grid(symbol(0.125), COARSE)
    assert "not a multiple of 0.25" in found.message
    assert lint(symbol(0.125), grid=COARSE) != lint(symbol(0.125))


def test_the_project_lints_with_the_librarys_grid():
    coarse = Library("S", "S", "", {"1": symbol(0.125)}, grid=COARSE)
    plain = Library("S", "S", "", {"1": symbol(0.125)})
    assert any(f.rule == "off-drawing-grid" for f in _lint_findings(coarse))
    assert not any(f.rule == "off-drawing-grid" for f in _lint_findings(plain))


def test_to_divisions_follows_the_librarys_divisions_per_module():
    parsed, _ = config("[grid]\nmodule_mm = 5\ndivisions_per_module = 4\n")
    assert to_divisions(parsed.grid, 0.75) == 3
    assert to_divisions(DEFAULT_GRID, 0.75) == 6
    with pytest.raises(ValueError, match=re.escape(repr(0.125))):
        to_divisions(parsed.grid, 0.125)


@pytest.mark.parametrize(
    ("args", "named"),
    [
        ((2.5, 3), "divisions_per_module 3"),
        ((2.5, 0), "divisions_per_module 0"),
        ((2.5, True), "divisions_per_module True"),
        ((0, 8), "module_mm 0"),
        ((-1.0, 8), "module_mm -1.0"),
        ((float("nan"), 8), "module_mm nan"),
    ],
)
def test_a_grid_built_by_hand_is_checked(args, named):
    with pytest.raises(ValueError, match=named):
        Grid(*args)


def test_the_error_names_the_fix():
    with pytest.raises(ValueError, match="use 1, 2, 4, 8"):
        Grid(2.5, 6)


def test_snap_and_on_grid_follow_the_given_grid():
    assert snap(0.3, COARSE) == 0.25
    assert snap(0.1) == snap(0.1, DEFAULT_GRID) == 0.125
    assert on_grid(0.25, grid=COARSE)
    assert not on_grid(0.125, grid=COARSE)
    assert on_grid(0.125)
