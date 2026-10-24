"""`text_tag` and `corner_text`: free text in millimetres (D100)."""

import pytest

from symdef import Box, FontMetrics, Point, TextPlacement, Weight, corner_text, text_tag, text_width
from symdef.errors import InvalidValueError
from symdef.slottext import Anchor
from symdef.svg import _num

FAMILY = "Test Sans"


def tag(
    anchor: Anchor = "start",
    *,
    turn: bool = False,
    weight: Weight = Weight.NORMAL,
    tint: str | None = None,
    muted: str | None = None,
) -> str:
    return text_tag(
        "K1",
        Point(10, 20.5),
        2.5,
        anchor=anchor,
        font_family=FAMILY,
        turn=turn,
        weight=weight,
        tint=tint,
        muted=muted,
    )


def test_a_tag_holds_the_string_the_point_the_size_and_the_anchor():
    assert tag(anchor="end") == (
        '<text x="10" y="20.5" font-size="2.5" text-anchor="end" fill="#000" stroke="none" '
        'font-family="Test Sans">K1</text>'
    )


@pytest.mark.parametrize("anchor", ["start", "middle", "end"])
def test_each_anchor_is_written(anchor):
    assert f'text-anchor="{anchor}"' in tag(anchor=anchor)


def test_a_turned_tag_rotates_about_its_point():
    assert 'transform="rotate(-90 10 20.5)"' in tag(turn=True)
    assert "transform" not in tag()


def test_thick_is_bold_and_normal_is_not():
    assert ' font-weight="bold"' in tag(weight=Weight.THICK)
    assert "font-weight" not in tag(weight=Weight.NORMAL)


def test_the_fill_is_muted_else_tint_else_black():
    assert 'fill="#000"' in tag()
    assert 'fill="red"' in tag(tint="red")
    assert 'fill="#999"' in tag(tint="red", muted="#999")


def test_a_bad_colour_raises():
    with pytest.raises(InvalidValueError):
        tag(tint='red" onload="x')
    with pytest.raises(InvalidValueError):
        tag(muted="#12")


def test_the_content_and_family_are_escaped():
    out = text_tag("a<b&c", Point(0, 0), 1, anchor="start", font_family='A"B')
    assert ">a&lt;b&amp;c</text>" in out
    assert "font-family='A\"B'" in out


BOX = Box(Point(10, 20), Point(30, 24))
CAP = 0.72 * 2.5


@pytest.mark.parametrize(
    ("corner", "point", "anchor"),
    [
        ("NW", Point(10, 20 + CAP), "start"),
        ("NE", Point(30, 20 + CAP), "end"),
        ("SW", Point(10, 24), "start"),
        ("SE", Point(30, 24), "end"),
    ],
)
def test_each_corner_gives_its_baseline_point_and_anchor(corner, point, anchor):
    got = corner_text(BOX, corner, 2.5, None)
    assert got == TextPlacement(point, anchor, turned=False)


def test_the_mapping_feeds_the_tag():
    placed = corner_text(BOX, "SE", 2.5, None)
    out = text_tag("K1", placed.point, 2.5, anchor=placed.anchor, font_family=FAMILY)
    assert 'x="30" y="24"' in out
    assert 'text-anchor="end"' in out


@pytest.mark.parametrize("corner", ["NW", "NE", "SW", "SE"])
def test_a_text_set_by_a_corner_lies_within_the_box_by_text_width(corner):
    placed = corner_text(BOX, corner, 2.5, None)
    width = text_width(None, "K1", 2.5)
    x0, x1 = (
        (placed.point.x, placed.point.x + width)
        if placed.anchor == "start"
        else (placed.point.x - width, placed.point.x)
    )
    if placed.anchor == "start":
        assert (x0, x1) == (BOX.min.x, BOX.min.x + width)
    else:
        assert (x0, x1) == (BOX.max.x - width, BOX.max.x)


@pytest.mark.parametrize("corner", ["SX", "XW", "NX"])
def test_an_unknown_corner_raises_and_names_it(corner):
    with pytest.raises(InvalidValueError) as err:
        corner_text(BOX, corner, 2.5, None)
    message = str(err.value)
    assert repr(corner) in message
    assert all(valid in message for valid in ("NW", "NE", "SW", "SE"))


# D117: classes, and where the point sits across the line.
ASCENT = FontMetrics(
    "F",
    2048,
    1493,
    1556,
    492,
    {Weight.NORMAL: {}, Weight.THICK: {}},
    {Weight.NORMAL: 1000, Weight.THICK: 1000},
)


def placed(**kw) -> str:
    return text_tag("K1", Point(10, 20), 4, anchor="middle", font_family=FAMILY, font=ASCENT, **kw)


def test_classes_lead_the_tag_are_escaped_and_leave_the_default_alone():
    assert tag().startswith("<text x=")
    assert tag_classes("symbol a").startswith('<text class="symbol a" x="10"')
    assert tag_classes('a"b').startswith("<text class='a\"b' x=")


def tag_classes(classes: str) -> str:
    return text_tag("K1", Point(10, 20.5), 2.5, anchor="start", font_family=FAMILY, classes=classes)


def test_top_puts_the_baseline_an_ascent_below_the_point():
    ascent = 1556 / 2048 * 4
    assert f'y="{_num(20 + ascent)}"' in placed(at="top")
    assert 'x="10"' in placed(at="top")
    assert placed(at="baseline") == placed()


def test_a_turned_top_moves_the_baseline_right_and_turns_about_it():
    shifted = _num(10 + 1556 / 2048 * 4)
    out = placed(at="top", turn=True)
    assert f'x="{shifted}" y="20"' in out
    assert f"rotate(-90 {shifted} 20)" in out


def test_centre_puts_the_em_box_half_a_font_either_side_of_the_point():
    ascent = 1556 / 2048 * 4
    out = placed(at="centre", turn=True)
    x = 10 - 4 / 2 + ascent
    assert f'x="{_num(x)}" y="20"' in out
    assert 'text-anchor="middle"' in out
    # the em box runs from the baseline back by the ascent and on by the descent side of the em
    assert x - ascent == 8.0
    assert x - ascent + 4 == 12.0
    assert placed(at="centre") != placed(at="top")


def test_top_and_centre_need_a_font_and_an_unknown_at_raises():
    for at in ("top", "centre"):
        with pytest.raises(
            InvalidValueError, match=rf"at='{at}' needs the font's ascent; pass font="
        ):
            text_tag("K1", Point(0, 0), 4, anchor="start", font_family=FAMILY, at=at)
    with pytest.raises(InvalidValueError, match="at 'bottom' is not valid"):
        text_tag(
            "K1",
            Point(0, 0),
            4,
            anchor="start",
            font_family=FAMILY,
            at="bottom",  # ty: ignore[invalid-argument-type] - a bad value
        )
