"""A loaded library's symbols cannot be assigned into (D78)."""

from pathlib import Path

import pytest

from symdef import load_bundle, load_library
from symdef.serialize import bundle_to_data, to_json

GUIDE = Path(__file__).resolve().parent / "fixtures" / "guide"


def test_load_library_freezes_the_symbols():
    library = load_library(GUIDE)
    with pytest.raises(TypeError):
        library.symbols["S99999"] = next(iter(library))  # ty: ignore[invalid-assignment]  # frozen on purpose


def test_load_bundle_freezes_the_symbols(tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(to_json(bundle_to_data(load_library(GUIDE))), encoding="utf-8")
    loaded = load_bundle(bundle)
    with pytest.raises(TypeError):
        loaded.symbols["S99999"] = next(iter(loaded))  # ty: ignore[invalid-assignment]  # frozen on purpose
