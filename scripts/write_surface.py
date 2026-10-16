"""Write `surface.toml`: the API surface by name, one sorted list per door.

An order names the move; a commit that changes the file also adds a line to docs/CHANGELOG.md.

Usage:
    uv run python scripts/write_surface.py
"""

import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SURFACE = ROOT / "surface.toml"
DOORS = ("symdef", "symdef.authoring")
HEADER = (
    "# The API surface by name: each door and the sorted names in its `__all__`.\n"
    "# tests/test_surface.py fails on any difference; an order names the surface move.\n"
    "# Regenerate by hand, in a commit that adds a docs/CHANGELOG.md line:\n"
    "#   uv run python scripts/write_surface.py\n"
    "\n[modules]\n"
)


def surface_text() -> str:
    """Return the text of `surface.toml` for the current `__all__` of each door."""
    lines = [
        f"{json.dumps(door)} = {json.dumps(sorted(importlib.import_module(door).__all__))}\n"
        for door in DOORS
    ]
    return HEADER + "".join(lines)


if __name__ == "__main__":
    SURFACE.write_text(surface_text(), encoding="utf-8")
