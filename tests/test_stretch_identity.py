"""Stretch, table and tutorial output keeps the 0.9.0 bytes in tests/fixtures/stretch_0_9."""

import pytest
from stretch_samples import GOLDEN, golden_files

FILES = golden_files()


def test_the_goldens_cover_the_whole_set():
    assert sorted(p.name for p in GOLDEN.iterdir()) == sorted(FILES)


@pytest.mark.parametrize("name", sorted(FILES))
def test_output_keeps_the_0_9_bytes(name):
    assert FILES[name] == (GOLDEN / name).read_bytes()
