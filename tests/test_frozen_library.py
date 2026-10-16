"""A loaded library's symbols cannot be assigned into (D78)."""

from pathlib import Path

import pytest

from symdef import load_bundle, load_library
from symdef.font import FontMetrics
from symdef.model import Centre
from symdef.serialize import bundle_to_data, to_json
from symdef.slottext import SIDE_ALIGN, TURNED_ALIGN

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


def test_font_advances_cannot_be_written_and_do_not_follow_the_source_dict():
    source = {"A": 500}
    font = FontMetrics("F", 1000, 700, 900, 200, source, 600)
    with pytest.raises(TypeError):
        font.advances["B"] = 1  # ty: ignore[invalid-assignment]  # frozen on purpose
    source["B"] = 1
    assert dict(font.advances) == {"A": 500}


@pytest.mark.parametrize("table", [SIDE_ALIGN, TURNED_ALIGN])
def test_the_align_tables_cannot_be_written(table):
    with pytest.raises(TypeError):
        table[Centre.C] = ("start", 0.0)
    with pytest.raises(TypeError):
        del table[Centre.C]  # frozen on purpose
