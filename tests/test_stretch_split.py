"""`[grid] stretch_split = "whole"`: a multi-cut growth splits in whole divisions (D97)."""

import json
from dataclasses import replace

import pytest
from test_fitted import HEAD, HEIGHT, LIB, MID, ROW, SHORT, WIDE
from test_grid import config, library

from symdef.boxes import body_box
from symdef.errors import InvalidValueError
from symdef.fitted import fitted_table
from symdef.geometry import Direction, Line, Point
from symdef.load import library_from_bundle, validate_bundle
from symdef.model import Anchor, Reference, Status, Stretch, Symbol, SymbolKind
from symdef.serialize import bundle_to_data, to_json
from symdef.stretch import stretch
from symdef.units import DEFAULT_GRID, Grid

WHOLE = Grid(stretch_split="whole")
D = WHOLE.division


def card(n_cuts):
    """A symbol 12 modules wide with `n_cuts` equal cuts and an anchor past each, along x."""
    cuts = tuple(Stretch("x", 2 * k) for k in range(1, n_cuts + 1))
    anchors = tuple(Anchor(f"a{k}", Point(2 * k + 3, 0), Direction.N) for k in range(n_cuts))
    return Symbol(
        "card",
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", "1"),
        (Line(Point(0, 0), Point(12, 0)),),
        anchors=anchors,
        stretch=cuts,
    )


def moves(symbol, grow, grid=WHOLE):
    """Each anchor's move, in divisions, after growing the symbol by `grow` divisions."""
    out = stretch(symbol, "x", 12 + grow * D, grid=grid)
    pairs = zip(out.anchors, symbol.anchors, strict=True)
    return [round((a.position.x - b.position.x) / D) for a, b in pairs]


@pytest.mark.parametrize(("grow", "near", "far"), [(7, 3, 4), (8, 4, 4), (1, 0, 1), (0, 0, 0)])
def test_two_cuts_give_the_near_one_the_floor_of_half(grow, near, far):
    assert near == grow // 2  # render's `w // 2`
    assert moves(card(2), grow)[0] == near
    assert moves(card(2), grow)[1] == near + far


@pytest.mark.parametrize(("grow", "shares"), [(7, (2, 2, 3)), (9, (3, 3, 3)), (8, (2, 2, 4))])
def test_three_equal_cuts_floor_each_near_share_and_the_far_one_takes_the_rest(grow, shares):
    got = moves(card(3), grow)
    assert [b - a for a, b in zip((0, *got), got, strict=False)] == [
        shares[0],
        shares[1],
        shares[2],
    ]


def test_the_shares_sum_to_the_growth_and_the_body_grows_by_it():
    for n, grow in ((2, 7), (3, 7), (3, 11), (4, 13)):
        out = stretch(card(n), "x", 12 + grow * D, grid=WHOLE)
        assert body_box(out).width == pytest.approx(12 + grow * D)
        assert moves(card(n), grow)[-1] == grow


def test_weights_pick_the_floored_shares():
    heavy = replace(card(2), stretch=(Stretch("x", 2, 1), Stretch("x", 4, 3)))
    assert moves(heavy, 10) == [2, 10]


def test_a_single_cut_takes_all_of_the_growth():
    assert moves(card(1), 7) == [7]


def test_a_growth_that_is_not_whole_divisions_raises_naming_symbol_and_fix():
    with pytest.raises(InvalidValueError, match=r"card: the growth .* whole number of divisions"):
        stretch(card(2), "x", 12 + 7.5 * D, grid=WHOLE)


def test_weight_split_and_no_grid_are_unchanged():
    a = stretch(card(2), "x", 12 + 7.5 * D)
    b = stretch(card(2), "x", 12 + 7.5 * D, grid=DEFAULT_GRID)
    assert a == b
    assert round((a.anchors[0].position.x - 3) / D, 6) == 3.75


def test_a_bad_value_names_the_key_the_value_and_the_two_legal_ones():
    with pytest.raises(InvalidValueError, match=r"stretch_split 'round'.*weight.*whole"):
        Grid(stretch_split="round")
    _, findings = config("[grid]\nmodule_mm = 5\ndivisions_per_module = 4\nstretch_split = 'x'\n")
    assert findings == ["must be one of weight, whole"]


def test_fitted_table_is_identical_under_both_splits():
    texts = [{"a": SHORT, "b": WIDE}, {"a": MID, "b": "A"}]
    weight = replace(LIB, grid=Grid(divisions_per_module=8))
    whole = replace(LIB, grid=Grid(divisions_per_module=8, stretch_split="whole"))
    assert whole.grid.stretch_split == "whole"
    head = replace(HEAD, stretch=(Stretch("x", 3), Stretch("x", 7.5)))
    a = fitted_table(ROW, "y", texts, weight, HEIGHT, head=head, head_texts={"h": WIDE})
    b = fitted_table(ROW, "y", texts, whole, HEIGHT, head=head, head_texts={"h": WIDE})
    assert a == b
    assert body_box(a).width > 10  # the columns did grow, on two cuts


def test_library_toml_declares_the_split_and_without_it_the_split_is_by_weight():
    parsed, findings = config(
        "[grid]\nmodule_mm = 5\ndivisions_per_module = 4\nstretch_split = 'whole'\n"
    )
    assert findings == []
    assert parsed.grid.stretch_split == "whole"
    plain, _ = config("[grid]\nmodule_mm = 5\ndivisions_per_module = 4\n")
    assert plain.grid.stretch_split == "weight"


def test_the_bundle_writes_the_split_only_when_it_is_whole_and_round_trips_it():
    coarse = Grid(module_mm=5, divisions_per_module=4)
    plain = json.loads(to_json(bundle_to_data(library(coarse))))
    assert "stretch_split" not in plain["grid"]
    data = json.loads(to_json(bundle_to_data(library(replace(coarse, stretch_split="whole")))))
    assert data["grid"]["stretch_split"] == "whole"
    assert validate_bundle(data) == ()
    assert library_from_bundle(data).grid.stretch_split == "whole"
