"""`[grid] outline_margin`: how far a unit outline stands off its contents, in divisions (D120)."""

import json
from dataclasses import replace

import pytest
from test_grid import config, library

from symdef.errors import InvalidValueError
from symdef.load import library_from_bundle, validate_bundle
from symdef.serialize import bundle_to_data, to_json
from symdef.units import DEFAULT_GRID, Grid

COARSE = "[grid]\nmodule_mm = 5\ndivisions_per_module = 4\n"


def test_there_is_no_default_margin():
    assert DEFAULT_GRID.outline_margin is None
    assert Grid(outline_margin=0).outline_margin == 0


@pytest.mark.parametrize("bad", [-1, 1.5, True, "8"])
def test_a_margin_that_is_not_whole_divisions_of_zero_or_more_raises(bad):
    with pytest.raises(InvalidValueError, match=r"outline_margin .*0 or more"):
        Grid(outline_margin=bad)


def test_library_toml_declares_the_margin_and_without_it_there_is_none():
    parsed, findings = config(COARSE + "outline_margin = 24\n")
    assert findings == []
    assert parsed.grid.outline_margin == 24
    plain, _ = config(COARSE)
    assert plain.grid.outline_margin is None


@pytest.mark.parametrize(
    ("bad", "message"),
    [("-2", "must be 0 or more"), ("1.5", "must be an integer"), ("'x'", "must be an integer")],
)
def test_a_bad_toml_margin_is_a_finding(bad, message):
    _, findings = config(COARSE + f"outline_margin = {bad}\n")
    assert findings == [message]


def test_the_bundle_writes_the_margin_only_when_the_library_declares_it_and_round_trips_it():
    coarse = Grid(module_mm=5, divisions_per_module=4)
    plain = json.loads(to_json(bundle_to_data(library(coarse))))
    assert "outline_margin" not in plain["grid"]
    data = json.loads(to_json(bundle_to_data(library(replace(coarse, outline_margin=24)))))
    assert data["grid"]["outline_margin"] == 24
    assert validate_bundle(data) == ()
    assert library_from_bundle(data).grid.outline_margin == 24
