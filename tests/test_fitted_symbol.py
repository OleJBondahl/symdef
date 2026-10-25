"""`fitted_symbol`: each slot's text holds in its slot, the symbol grows where it must (D95)."""

import math

import pytest
from test_font import FONT

from symdef.boxes import body_box, slot_box
from symdef.errors import InvalidValueError, UnknownNameError
from symdef.fitted import fitted_symbol
from symdef.font import text_width
from symdef.geometry import Direction, Line, Point
from symdef.model import Library, Reference, Slot, Status, Stretch, Symbol, SymbolKind
from symdef.slottext import text_box
from symdef.units import Grid

HEIGHT = 2
LIB = Library("S", "S", "", {}, font=FONT, grid=Grid(divisions_per_module=8))
SHORT, MID, WIDE = "AB", "ABiAB", "ABiABAB"
BODY = (Line(Point(0, 0), Point(10, 0)), Line(Point(0, 4), Point(10, 4)))


def up(text):
    """The text's width at HEIGHT in modules, rounded up to eighths, worked apart from symdef."""
    return math.ceil(round(text_width(FONT, text, HEIGHT) * 8, 6)) / 8


def eighths(value):
    """A height in modules rounded up to eighths, worked apart from symdef."""
    return math.ceil(round(value * 8, 6)) / 8


def build(*slots, cuts=()):
    return Symbol(
        "cell",
        SymbolKind.SYMBOL,
        Status.UNVERIFIED,
        Reference("X", "1"),
        BODY,
        slots=slots,
        stretch=cuts,
    )


def by_id(symbol, slot_id):
    return next(s for s in symbol.slots if s.id == slot_id)


def test_a_planted_wider_text_grows_the_slot_to_its_width_rounded_up():
    symbol = build(
        Slot("a", Point(1, 1), Direction.E, (4, 2)),
        cuts=(Stretch("x", 3),),
    )
    result = fitted_symbol(symbol, {"a": WIDE}, LIB, HEIGHT)
    assert isinstance(result, Symbol)
    assert slot_box(by_id(result, "a")).width == up(WIDE)
    assert body_box(result).width == 10 + up(WIDE) - 4


def test_a_two_line_text_grows_the_slot_to_its_block_height_rounded_up():
    slot = Slot("a", Point(1, 1), Direction.E, (4, 0.5))
    symbol = build(slot, cuts=(Stretch("y", 1.1),))
    result = fitted_symbol(symbol, {"a": "AB\nCD"}, LIB, HEIGHT)
    block = text_box(slot, "AB\nCD", HEIGHT, FONT).height
    assert slot_box(by_id(result, "a")).height == eighths(block)
    assert body_box(result).height == 4 + eighths(block) - 0.5


def test_a_turned_slot_grows_along_y_for_its_text_length():
    slot = Slot("a", Point(1, 1), Direction.E, (1, 2), turn=True)
    symbol = build(slot, cuts=(Stretch("y", 1.5), Stretch("x", 1.5)))
    result = fitted_symbol(symbol, {"a": WIDE}, LIB, HEIGHT)
    assert slot_box(by_id(result, "a")).height == up(WIDE)


def test_a_text_that_fits_changes_nothing_even_without_cuts():
    symbol = build(Slot("a", Point(1, 1), Direction.E, (4, 2)))
    assert fitted_symbol(symbol, {"a": SHORT}, LIB, HEIGHT) == symbol


def test_a_text_that_fits_changes_nothing_with_cuts():
    symbol = build(
        Slot("a", Point(1, 1), Direction.E, (4, 2)),
        cuts=(Stretch("x", 3),),
    )
    assert fitted_symbol(symbol, {"a": SHORT}, LIB, HEIGHT) == symbol


def test_a_slot_that_must_grow_without_a_cut_across_it_raises_naming_it():
    symbol = build(Slot("a", Point(1, 1), Direction.E, (4, 2)))
    with pytest.raises(InvalidValueError, match="'a'"):
        fitted_symbol(symbol, {"a": WIDE}, LIB, HEIGHT)


def test_an_unknown_slot_id_raises():
    symbol = build(Slot("a", Point(1, 1), Direction.E, (4, 2)))
    with pytest.raises(UnknownNameError):
        fitted_symbol(symbol, {"zz": SHORT}, LIB, HEIGHT)


def test_a_text_height_of_zero_raises():
    symbol = build(Slot("a", Point(1, 1), Direction.E, (4, 2)))
    with pytest.raises(InvalidValueError):
        fitted_symbol(symbol, {"a": SHORT}, LIB, 0)


def test_a_text_one_division_wider_than_its_slot_widens_the_symbol_by_one_division():
    # The slot is one eighth narrower than the text's width rounded up: one division of growth.
    slot = Slot("a", Point(1, 1), Direction.E, (up(MID) - 0.125, 2))
    symbol = build(slot, cuts=(Stretch("x", 3),))
    result = fitted_symbol(symbol, {"a": MID}, LIB, HEIGHT)
    assert slot_box(by_id(result, "a")).width == up(MID)
    assert body_box(result).width - body_box(symbol).width == pytest.approx(0.125)
