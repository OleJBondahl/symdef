"""symdef's own errors: each class from a real call, and no builtin raise left in the package."""

import ast
from pathlib import Path

import pytest
from build_symbol import PLAIN

from symdef import (
    Direction,
    Grid,
    Library,
    Point,
    Port,
    Weight,
    leads,
    repeat,
    stretch,
    table,
    to_fragment,
    to_fragment_mm,
    wire,
)
from symdef.boxes import slot_box
from symdef.errors import InvalidValueError, SymdefError, UnknownNameError
from symdef.geometry import Box
from symdef.model import Slot
from symdef.units import to_divisions

SRC = Path(__file__).resolve().parent.parent / "src" / "symdef"
LIBRARY = Library("IEC 60617", "IEC 60617", "", {}, wires=())


def with_port():
    from dataclasses import replace

    return replace(PLAIN, ports=(Port("a", Point(0, 1), Direction.S),))


def test_both_classes_sit_under_the_base():
    assert issubclass(InvalidValueError, SymdefError)
    assert issubclass(UnknownNameError, SymdefError)
    assert not issubclass(InvalidValueError, ValueError)
    assert not issubclass(UnknownNameError, KeyError)


def test_an_invalid_value_names_the_value_and_what_is_valid():
    with pytest.raises(
        InvalidValueError, match=r"3 is not a power of two; use 1, 2, 4, 8"
    ) as caught:
        Grid(divisions_per_module=3)
    assert "3" in str(caught.value)
    with pytest.raises(InvalidValueError, match=r"0\.3333"):
        to_divisions(Grid(), 1 / 3)


def test_an_unknown_name_lists_the_valid_names():
    with pytest.raises(UnknownNameError) as caught:
        leads(with_port(), ("zz",))
    assert "'zz'" in str(caught.value)
    assert "['a']" in str(caught.value)


def test_wire_names_the_unknown_style_and_the_valid_ones():
    with pytest.raises(UnknownNameError, match=r"'nope'.*none"):
        wire(LIBRARY, "nope", [(0, 0), (1, 0)])


def test_the_small_sites_raise_the_domain_errors():
    with pytest.raises(InvalidValueError, match="at least one box"):
        Box.union()
    with pytest.raises(InvalidValueError, match="needs a height"):
        slot_box(Slot("tag", Point(0, 0), Direction.N, (2, 1)), "x", None)
    with pytest.raises(InvalidValueError, match="pole count"):
        repeat(PLAIN, 0)
    with pytest.raises(InvalidValueError, match="between 1 and 64"):
        table(PLAIN, 0, "y")


def test_stretch_raises_the_domain_error():
    with pytest.raises(InvalidValueError, match="no stretch on the x axis"):
        stretch(PLAIN, "x", 5)


def test_svg_raises_the_domain_errors():
    with pytest.raises(InvalidValueError, match="tint must be"):
        to_fragment(PLAIN, tint="<")
    with pytest.raises(UnknownNameError, match=r"nope.*the slots are"):
        to_fragment(PLAIN, texts={"nope": "x"})


def test_svg_mm_raises_the_domain_errors():
    with pytest.raises(UnknownNameError, match=r"no width for NORMAL.*it has none"):
        to_fragment_mm(
            PLAIN,
            module_mm=3,
            weights_mm={},
            dash_mm=(1, 1),
            font_family="x",
            font_mm=1,
            cap_ratio=0.7,
        )
    assert Weight.NORMAL


def raise_sites(source: str) -> list[str]:
    """Return the builtin errors a source raises by name (ValueError, KeyError, OSError)."""
    banned = {"ValueError", "KeyError", "OSError"}
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Raise) and node.exc is not None:
            call = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if isinstance(call, ast.Name) and call.id in banned:
                found.append(f"{call.id}@{node.lineno}")
    return found


def test_no_module_raises_a_builtin_error():
    found = {p.name: raise_sites(p.read_text()) for p in SRC.rglob("*.py")}
    assert {name: sites for name, sites in found.items() if sites} == {}


def test_the_gate_can_fail():
    assert raise_sites("raise ValueError('x')\nraise KeyError\n") == ["ValueError@1", "KeyError@2"]
