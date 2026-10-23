"""`rect_mm`, `outline_mm` and `line_mm`: widths and dashes are library data (D117)."""

import re
import xml.etree.ElementTree as ET

import pytest

from symdef import Library, Weight, line_mm, outline_mm, rect_mm
from symdef.errors import InvalidValueError, UnknownNameError

LONG = (4.0, 1.0)


def lib(normal=0.25, thick=0.5, dash=None) -> Library:
    lines = {Weight.NORMAL: normal, Weight.THICK: thick}
    return Library(
        "s",
        "s",
        "",
        {},
        lines=lines,
        dash={"long": LONG, "dot": (0.5, 0.5, 0.1, 0.5)} | (dash or {}),
    )


def rect(library=None, **kw) -> str:
    args = {"weight": Weight.NORMAL, "stroke": "#000", "fill": "none"} | kw
    return rect_mm((1, 2, 3, 4), library=lib() if library is None else library, **args)


def test_a_rect_writes_the_geometry_the_paint_and_the_library_width():
    assert rect() == (
        '<rect x="1" y="2" width="3" height="4" fill="none" stroke="#000" stroke-width="0.25"/>'
    )


def test_stroke_and_fill_are_written_as_given():
    out = rect(stroke="red", fill="#abc")
    assert 'fill="#abc" stroke="red"' in out


@pytest.mark.parametrize("weight", [Weight.NORMAL, Weight.THICK])
def test_every_shape_writes_the_library_width_of_its_weight(weight):
    library = lib(normal=0.31, thick=0.77)
    width = {Weight.NORMAL: "0.31", Weight.THICK: "0.77"}[weight]
    shapes = (
        rect(library, weight=weight),
        line_mm((0, 0), (1, 0), library=library, weight=weight, stroke="#000"),
        outline_mm((0, 0, 1, 1), library=library, weight=weight, stroke="#000"),
        outline_mm((0, 0, 1, 1), library=library, weight=weight, stroke="#000", dash="long"),
    )
    for shape in shapes:
        assert set(re.findall(r'stroke-width="([^"]*)"', shape)) == {width}


def test_a_dash_is_the_library_key_and_none_writes_none():
    assert 'stroke-dasharray="4 1"' in rect(dash="long")
    assert "stroke-dasharray" not in rect()
    assert 'stroke-dasharray="0.5 0.5 0.1 0.5"' in rect(dash="dot")
    other = lib(dash={"long": (9.0, 2.5)})
    assert 'stroke-dasharray="9 2.5"' in rect(other, dash="long")


def test_classes_are_the_leading_attribute_and_are_escaped():
    assert rect(classes="symbol box").startswith('<rect class="symbol box" x="1"')
    assert rect(classes='a"b').startswith("<rect class='a\"b' x=")
    assert " class=" not in rect()


def test_a_line_writes_its_ends():
    out = line_mm((1, 2), (3.5, 2), library=lib(), weight=Weight.THICK, stroke="#111", classes="c")
    assert out == (
        '<line class="c" x1="1" y1="2" x2="3.5" y2="2" stroke="#111" stroke-width="0.5"/>'
    )


def test_a_solid_outline_is_one_unfilled_rect():
    out = outline_mm((1, 2, 3, 4), library=lib(), weight=Weight.NORMAL, stroke="#000")
    assert out == rect(fill="none")


def test_a_dashed_outline_is_four_edges_top_bottom_left_right_each_from_its_left_or_top_end():
    out = outline_mm(
        (1, 2, 3, 4), library=lib(), weight=Weight.NORMAL, stroke="#000", dash="long", classes="o"
    )
    edges = re.findall(r'x1="(\S+)" y1="(\S+)" x2="(\S+)" y2="(\S+)"', out)
    assert edges == [
        ("1", "2", "4", "2"),
        ("1", "6", "4", "6"),
        ("1", "2", "1", "6"),
        ("4", "2", "4", "6"),
    ]
    assert out.count("<line") == 4
    assert out.count('stroke-dasharray="4 1"') == 4
    assert out.count('class="o"') == 4


def test_numbers_are_symdefs_own_four_decimals_half_even():
    # one grid unit at a 2.5 mm module is 0.3125 mm, half a unit 0.15625 mm
    out = rect_mm(
        (0.15625, 0.3125, 0.46875, 1.0),
        library=lib(),
        weight=Weight.NORMAL,
        stroke="#000",
        fill="none",
    )
    assert 'x="0.1562" y="0.3125" width="0.4688" height="1"' in out


def test_the_shapes_are_well_formed_xml():
    body = (
        rect(classes="a&b")
        + line_mm((0, 0), (1, 1), library=lib(), weight=Weight.NORMAL, stroke="red", dash="long")
        + outline_mm((0, 0, 2, 2), library=lib(), weight=Weight.NORMAL, stroke="#000", dash="long")
    )
    root = ET.fromstring(f"<svg>{body}</svg>")  # noqa: S314 - our own output
    assert [e.tag for e in root] == ["rect", "line", "line", "line", "line", "line"]


def test_an_unknown_dash_key_names_it_and_the_fix():
    with pytest.raises(
        UnknownNameError, match=r"'nope'.*long.*pass a library with that \[dash\] key"
    ):
        rect(dash="nope")
    with pytest.raises(UnknownNameError, match="it has none"):
        rect(Library("s", "s", "", {}, lines={Weight.NORMAL: 0.25}), dash="long")


def test_a_weight_the_library_lacks_raises_and_names_what_it_has():
    with pytest.raises(
        UnknownNameError, match=r"no width for RULE.*it has NORMAL, THICK.*\[lines\]"
    ):
        rect(weight=Weight.RULE)
    with pytest.raises(UnknownNameError, match="it has none"):
        rect(Library("s", "s", "", {}), weight=Weight.NORMAL)


@pytest.mark.parametrize("box", [(0, 0, -1, 1), (0, 0, 1, -1)])
def test_a_negative_box_raises_with_a_fix(box):
    for call, name in ((rect_mm, "rect_mm"), (outline_mm, "outline_mm")):
        kw = {"fill": "none"} if call is rect_mm else {}
        with pytest.raises(
            InvalidValueError,
            match=rf"{name}: box size .* must not be negative; pass a positive size",
        ):
            call(box, library=lib(), weight=Weight.NORMAL, stroke="#000", **kw)
    with pytest.raises(InvalidValueError, match="outline_mm"):
        outline_mm(box, library=lib(), weight=Weight.NORMAL, stroke="#000", dash="long")


def test_a_bad_colour_cannot_inject_markup():
    with pytest.raises(InvalidValueError, match="stroke must be"):
        rect(stroke='red" onload="x')
    with pytest.raises(InvalidValueError, match="fill must be"):
        rect(fill="<")


def test_weight_is_required_on_every_shape():
    with pytest.raises(TypeError):
        rect_mm((0, 0, 1, 1), library=lib(), stroke="#000", fill="none")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        line_mm((0, 0), (1, 1), library=lib(), stroke="#000")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        outline_mm((0, 0, 1, 1), library=lib(), stroke="#000")  # type: ignore[call-arg]
