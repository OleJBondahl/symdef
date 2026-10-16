"""`surface.toml` lists the names of each door; any difference from `__all__` fails (D85)."""

import importlib
import importlib.util
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "write_surface", ROOT / "scripts" / "write_surface.py"
)
assert _spec is not None
assert _spec.loader is not None
write_surface = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(write_surface)

SNAPSHOT = tomllib.loads((ROOT / "surface.toml").read_text(encoding="utf-8"))["modules"]


@pytest.mark.parametrize("door", write_surface.DOORS)
def test_the_snapshot_is_the_doors_all(door):
    assert SNAPSHOT[door] == sorted(importlib.import_module(door).__all__)


def test_the_snapshot_holds_exactly_the_two_doors():
    assert sorted(SNAPSHOT) == sorted(write_surface.DOORS)


def test_the_file_is_what_the_script_writes():
    assert (ROOT / "surface.toml").read_text(encoding="utf-8") == write_surface.surface_text()
