"""`docs/CHANGELOG.md` has a section for the current `LIBRARY_VERSION` and a short opening (D85)."""

import re
from pathlib import Path

import symdef

CHANGELOG = (Path(__file__).resolve().parent.parent / "docs" / "CHANGELOG.md").read_text(
    encoding="utf-8"
)
HEADINGS = re.findall(r"^## (\S+)", CHANGELOG, flags=re.MULTILINE)


def test_the_current_version_has_a_section_with_a_line():
    assert symdef.LIBRARY_VERSION in HEADINGS
    section = CHANGELOG.split(f"## {symdef.LIBRARY_VERSION}", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"^- ", section, flags=re.MULTILINE)


def test_the_newest_section_is_the_current_version():
    assert HEADINGS[0] == symdef.LIBRARY_VERSION


def test_the_page_opens_with_a_short_paragraph_before_its_first_section():
    intro = CHANGELOG.split("\n## ", 1)[0].split("\n", 1)[1].strip()
    assert intro
    assert len(intro.splitlines()) <= 3
