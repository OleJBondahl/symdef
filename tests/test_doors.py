"""The consumer door `symdef` and the author door `symdef.authoring` share no name (D84)."""

import pytest

import symdef
import symdef.authoring

AUTHOR_NAMES = [
    "RULES",
    "LibraryConfig",
    "build",
    "check",
    "finding_key",
    "init",
    "lint",
    "stale_build",
    "write_build",
]


def test_the_two_doors_share_no_name():
    assert set(symdef.__all__).isdisjoint(symdef.authoring.__all__)


def test_every_listed_name_exists_on_its_door():
    assert all(hasattr(symdef, n) for n in symdef.__all__)
    assert all(hasattr(symdef.authoring, n) for n in symdef.authoring.__all__)


def test_an_author_name_is_not_importable_from_the_consumer_door():
    with pytest.raises(ImportError):
        exec("from symdef import build")  # noqa: S102 - the import statement is the test


def test_the_author_door_lists_its_names():
    assert sorted(symdef.authoring.__all__) == sorted(AUTHOR_NAMES)
