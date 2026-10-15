"""Without `texts`, both fragment functions draw the exact bytes of symdef 0.8.0."""

from pathlib import Path
from typing import Any

import pytest

import symdef
from symdef import Weight

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).parent / "fixtures" / "slot_text_0_8"
LIBRARY = symdef.load_library(ROOT / "docs" / "tutorial-set")
NUMBERS = sorted(LIBRARY.symbols)
MM: dict[str, Any] = {
    "module_mm": 2.5,
    "weights_mm": {Weight.NORMAL: 0.25, Weight.THICK: 0.5},
    "dash_mm": (1.2, 0.6),
    "dash_dot_mm": (3.0, 0.6, 0.6, 0.6),
    "font_family": "Inter, sans-serif",
    "font_mm": 2.0,
    "cap_ratio": 0.7,
}


def test_the_goldens_cover_the_whole_set():
    assert len(NUMBERS) == 9
    assert sorted(p.name for p in GOLDEN.iterdir()) == sorted(
        f"{n}{ext}" for n in NUMBERS for ext in (".svg", ".mm.svg")
    )


@pytest.mark.parametrize("number", NUMBERS)
def test_to_fragment_keeps_the_0_8_bytes(number):
    assert (
        symdef.to_fragment(LIBRARY.get(number)).encode() == (GOLDEN / f"{number}.svg").read_bytes()
    )


@pytest.mark.parametrize("number", NUMBERS)
def test_to_fragment_mm_keeps_the_0_8_bytes(number):
    got = symdef.to_fragment_mm(LIBRARY.get(number), **MM).encode()
    assert got == (GOLDEN / f"{number}.mm.svg").read_bytes()


@pytest.mark.parametrize("number", NUMBERS)
def test_texts_none_equals_no_keyword(number):
    symbol = LIBRARY.get(number)
    assert (
        symdef.to_fragment(symbol, texts=None).encode() == (GOLDEN / f"{number}.svg").read_bytes()
    )
    got = symdef.to_fragment_mm(symbol, texts=None, **MM).encode()
    assert got == (GOLDEN / f"{number}.mm.svg").read_bytes()
