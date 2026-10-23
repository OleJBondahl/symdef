"""R461: the words about `tag_roots` are general; no electrical or project word is in them."""

import inspect
import re
from pathlib import Path

import pytest

import symdef

GUIDE = Path(__file__).resolve().parent.parent / "docs" / "GUIDE.md"
BANNED = (
    *("electrical", "contact", "coil", "relay", "designation", "layout", "render"),
    *("schematic", "circuit", "breaker", "terminal"),
)


def guide_section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index("## The text root of a tag slot")
    return text[start : text.index("\n## ", start + 1)]


def banned_in(text: str) -> list[str]:
    words = set(re.findall(r"[a-z]+", text.lower()))
    return [word for word in BANNED if word in words]


def test_the_wording_check_can_fail():
    assert banned_in("a make contact") == ["contact"]
    assert banned_in("the text root of a symbol's tag slot") == []


@pytest.mark.parametrize(
    "words",
    [inspect.getdoc(symdef.tag_roots), inspect.getdoc(symdef.TextRoot), guide_section()],
    ids=["tag_roots", "TextRoot", "GUIDE section"],
)
def test_no_banned_word_is_in_the_words(words):
    assert banned_in(words) == []
