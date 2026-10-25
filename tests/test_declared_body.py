"""A symbol declares its body and keep-out box (D98): boxes, stretch, orient, lint, load."""

from dataclasses import replace

import pytest
from build_symbol import PLAIN, plain_symbol
from roundtrip import round_trips
from test_resolve import HEAD, resolve

from symdef.boxes import body_box, keepout_box, slot_box
from symdef.errors import InvalidValueError
from symdef.geometry import Box, Circle, Direction, Line, Orientation, Point, Polyline, Text
from symdef.lint import lint
from symdef.lint.textbody import text_outside_body
from symdef.load import parse_toml, symbol_from_data, validate
from symdef.model import Path, Port, Slot, Stretch, Symbol
from symdef.orient import orient, translate
from symdef.repeat import repeat
from symdef.serialize import symbol_to_data
from symdef.stretch import stretch
from symdef.svg import to_svg
from symdef.table import table


def box(x0, y0, x1, y1) -> Box:
    return Box(Point(x0, y0), Point(x1, y1))


def framed(**changes) -> Symbol:
    """A line 2 wide whose declared body is 6 by 4, cut at x = 1."""
    base = plain_symbol(
        elements=(Line(Point(0, 0), Point(2, 0)),),
        body=box(-1, -2, 5, 2),
        stretch=(Stretch("x", 1),),
    )
    return replace(base, **changes)


class TestBoxes:
    def test_the_declared_body_is_the_body_box(self):
        assert body_box(framed()) == box(-1, -2, 5, 2)

    def test_undeclared_the_body_is_the_element_extent(self):
        assert body_box(PLAIN) == box(0, 0, 0, 1)

    def test_the_keepout_is_the_declared_body_and_a_slot_does_not_enlarge_it(self):
        slot = Slot("tag", Point(5, 0), Direction.E, (2, 1))
        assert keepout_box(framed(slots=(slot,))) == keepout_box(framed()) == box(-1, -2, 5, 2)
        assert slot_box(slot) == box(5, -0.5, 7, 0.5)

    def test_a_declared_keepout_is_returned_as_declared(self):
        assert keepout_box(framed(keepout=box(-3, -3, 9, 3))) == box(-3, -3, 9, 3)


class TestStretch:
    def test_the_declared_box_grows_on_the_stretched_axis_only(self):
        grown = stretch(framed(), "x", 10)
        assert body_box(grown) == box(-1, -2, 9, 2)

    def test_the_other_axis_is_unchanged(self):
        sym = framed(stretch=(Stretch("y", 0),))
        assert body_box(stretch(sym, "y", 6)) == box(-1, -2, 5, 4)

    def test_a_declared_keepout_grows_the_same_way(self):
        grown = stretch(framed(keepout=box(-2, -3, 6, 3)), "x", 10)
        assert keepout_box(grown) == box(-2, -3, 10, 3)


class TestOrientAndCompose:
    @pytest.mark.parametrize("o", list(Orientation))
    def test_orient_turns_the_declared_box_like_the_element_extent(self, o):
        sym = plain_symbol(
            elements=(Polyline((Point(-1, -2), Point(5, 2))),), body=box(-1, -2, 5, 2)
        )
        assert body_box(orient(sym, o)) == body_box(orient(replace(sym, body=None), o))

    def test_translate_moves_the_declared_box(self):
        assert body_box(translate(framed(), 3, 1)) == box(2, -1, 8, 3)

    def test_repeat_unites_the_declared_boxes_of_the_poles(self):
        sym = framed(
            stretch=(),
            ports=(Port("in", Point(0, -2), Direction.N), Port("out", Point(0, 2), Direction.S)),
            paths=(Path("in", "out", "switch_open", through=True),),
        )
        assert body_box(repeat(sym, 1, port_format="{k}.{port}")) == box(-1, -2, 5, 2)
        assert body_box(repeat(sym, 3, port_format="{k}.{port}")) == box(-1, -2, 13, 2)

    def test_table_unites_the_rows_and_stretches_the_head(self):
        row = plain_symbol(elements=(Line(Point(0, 0), Point(2, 0)),), body=box(0, 0, 4, 2))
        head = plain_symbol(
            elements=(Line(Point(0, 0), Point(0, 1)),),
            body=box(0, -1, 4, 0),
            stretch=(Stretch("y", -1),),
        )
        made = table(row, 3, "y", port_format="{k}.{port}")
        assert body_box(made) == box(0, 0, 4, 6)
        assert body_box(table(row, 2, "y", head, port_format="{k}.{port}")) == box(0, -1, 4, 4)

    def test_a_part_that_declares_a_body_needs_the_composite_to_declare_one(self):
        part = (
            HEAD.format(name="Part", kind="element", number="sym-t")
            + "body = [0, 0, 2, 2]\nelements = [{ line = [[0, 0], [1, 0]] }]\n"
        )
        user = HEAD.format(name="User", kind="element", number="sym-u") + (
            'parts = [{ as = "a", use = "sym-t" }]\n'
        )
        found = resolve(part, user).findings["sym-u"]
        assert [(f.rule, f.location) for f in found] == [("schema", "/parts/0")]
        assert "declare `body`" in found[0].message
        own = resolve(part, user + "body = [0, 0, 3, 3]\n")
        assert own.findings == {}
        assert body_box(own.symbols["sym-u"]) == box(0, 0, 3, 3)


class TestLint:
    def test_an_element_outside_the_declared_body_is_reported(self):
        sym = plain_symbol(elements=(Line(Point(0, 0), Point(3, 0)),), body=box(0, 0, 2, 2))
        found = [f for f in lint(sym) if f.rule == "element-outside-body"]
        assert [(f.location, f.severity.name) for f in found] == [("elements[0]", "ERROR")]
        assert "'Plain'" in found[0].message
        assert "elements[0] (line)" in found[0].message

    def test_it_is_silent_when_every_element_lies_inside(self):
        sym = plain_symbol(
            elements=(Line(Point(0, 0), Point(2, 0)), Circle(Point(1, 1), 1)),
            body=box(0, 0, 2, 2),
        )
        assert [f for f in lint(sym) if f.rule == "element-outside-body"] == []

    def test_a_symbol_without_a_declared_body_is_not_checked(self):
        sym = plain_symbol(elements=(Line(Point(0, 0), Point(30, 0)),))
        assert [f for f in lint(sym) if f.rule == "element-outside-body"] == []

    def test_text_is_left_to_text_outside_body_which_uses_the_declared_body(self):
        sym = plain_symbol(
            elements=(Line(Point(0, 0), Point(4, 0)), Text("AAAAAAAA", Point(1, 0), 1)),
            body=box(0, -1, 4, 1),
        )
        assert [f for f in lint(sym) if f.rule == "element-outside-body"] == []
        assert [f.location for f in text_outside_body(sym, None, 2.5)] == ["elements[1]"]
        wide = replace(sym, body=box(-9, -1, 9, 1))
        assert text_outside_body(wide, None, 2.5) == ()


class TestLoad:
    TEXT = (
        HEAD.format(name="Framed", kind="element", number="sym-a")
        + "body = [0, 0, 4, 2]\nkeepout = [-1, -1, 5, 3]\n"
        + "elements = [{ line = [[0, 0], [1, 0]] }]\n"
    )

    def test_the_keys_load_and_round_trip_through_the_resolved_form(self):
        data, _ = parse_toml(self.TEXT)
        assert data is not None
        assert validate(data) == ()
        sym = symbol_from_data(data)
        assert (sym.body, sym.keepout) == (box(0, 0, 4, 2), box(-1, -1, 5, 3))
        assert round_trips(sym)
        out = symbol_to_data(sym)
        assert (out["body"], out["keepout"]) == ([0, 0, 4, 2], [-1, -1, 5, 3])
        assert out["body_box"] == [[0, 0], [4, 2]]

    def test_an_undeclared_symbol_writes_neither_key(self):
        assert {"body", "keepout"} & set(symbol_to_data(PLAIN)) == set()

    @pytest.mark.parametrize(
        ("value", "location"),
        [("[0, 0, 4]", "/body"), ("[4, 0, 0, 2]", "/body"), ("[0, 2, 4, 2]", "/body")],
    )
    def test_a_malformed_declaration_names_the_symbol_and_the_fix(self, value, location):
        text = self.TEXT.replace("body = [0, 0, 4, 2]", f"body = {value}")
        data, _ = parse_toml(text)
        found = validate(data)
        assert [f.location for f in found if f.location == location] == [location]
        if value != "[0, 0, 4]":
            assert "symbol 'Framed'" in found[0].message
            assert "needs x0 < x1" in found[0].message

    def test_a_malformed_keepout_is_refused_too(self):
        data, _ = parse_toml(
            self.TEXT.replace("keepout = [-1, -1, 5, 3]", "keepout = [5, 3, -1, -1]")
        )
        assert [f.location for f in validate(data)] == ["/keepout"]


def test_the_stretch_error_is_unchanged_for_a_declared_body_below_the_natural_extent():
    with pytest.raises(InvalidValueError):
        stretch(framed(), "x", 5)


class TestSvg:
    LINE = (Line(Point(0, 0), Point(2, 0)),)

    def test_the_view_holds_an_element_that_leaves_the_declared_body(self):
        leaving = to_svg(plain_symbol(elements=self.LINE, body=box(0, 0, 1, 1)))
        assert leaving == to_svg(plain_symbol(elements=self.LINE, body=box(0, 0, 2, 1)))

    def test_the_view_holds_the_whole_declared_body(self):
        plain = to_svg(plain_symbol(elements=self.LINE))
        assert to_svg(plain_symbol(elements=self.LINE, body=box(-3, 0, 5, 1))) != plain
