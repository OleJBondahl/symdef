"""A `between` element is drawn by `table` in every row but the last, and survives transforms."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from roundtrip import round_trips

from symdef import model
from symdef.files import load_library
from symdef.geometry import Direction, Line, Orientation, Point, Polyline, Style, Weight
from symdef.load import parse_toml, symbol_from_data, validate
from symdef.orient import orient, translate
from symdef.repeat import repeat
from symdef.serialize import symbol_to_data
from symdef.stretch import stretch
from symdef.table import table

ROOT = Path(__file__).resolve().parent.parent


def row() -> model.Symbol:
    """A row two units high and four wide: a lead to `in`, a marking slot, a through path."""
    return model.Symbol(
        name="row",
        kind=model.SymbolKind.SYMBOL,
        status=model.Status.UNVERIFIED,
        reference=model.Reference("X", "1"),
        elements=(
            Line(Point(0, -1), Point(4, -1), Weight.NORMAL, Style.SOLID),
            Line(Point(0, 1), Point(4, 1), Weight.NORMAL, Style.SOLID),
            Line(Point(-2, 0), Point(0, 0), Weight.NORMAL, Style.SOLID, port="in"),
        ),
        ports=(
            model.Port("in", Point(-2, 0), Direction.W),
            model.Port("out", Point(4, 0), Direction.E),
        ),
        paths=(model.Path("in", "out", "conductor", through=True),),
        slots=(
            model.Slot("marking.in", Point(-2, 0), Direction.W, (1, 1)),
            model.Slot("x", Point(2, 0), Direction.N, (1, 1)),
        ),
    )


TICK = Line(Point(2, -1), Point(2, 1), Weight.NORMAL, Style.SOLID, between=True)


def ticked() -> model.Symbol:
    """The row with one `between` tick in the middle."""
    return replace(row(), elements=(*row().elements, TICK))


def betweens(symbol: model.Symbol) -> list:
    """Return the elements of a symbol that carry `between`."""
    return [e for e in symbol.elements if isinstance(e, Line | Polyline) and e.between]


def test_a_between_element_is_drawn_in_every_row_but_the_last():
    base = row()
    t = table(ticked(), 4, "x", port_format="{k}.{port}")
    assert len(betweens(t)) == 3
    assert len([e for e in t.elements if not getattr(e, "between", False)]) == 4 * len(
        base.elements
    )


@pytest.mark.parametrize(("n", "count"), [(1, 0), (2, 1)])
def test_a_single_row_draws_none_and_two_rows_draw_one(n, count):
    assert len(betweens(table(ticked(), n, "x", port_format="{k}.{port}"))) == count


def test_without_a_between_element_table_draws_every_element():
    assert len(table(row(), 4, "x", port_format="{k}.{port}").elements) == 4 * len(row().elements)


def test_between_survives_orient_translate_stretch_and_repeat():
    assert len(betweens(orient(ticked(), Orientation.R90))) == 1
    assert len(betweens(translate(ticked(), 1, 1))) == 1
    cut = replace(ticked(), stretch=(model.Stretch("x", 2),))
    assert len(betweens(stretch(cut, "x", 8))) == 1
    assert len(betweens(repeat(ticked(), 2, port_format="{k}.{port}"))) == 2


def test_serialize_writes_between_only_on_the_element_that_has_it():
    elements = symbol_to_data(ticked())["elements"]
    assert [e for e in elements if "between" in e] == [elements[3]]
    assert elements[3]["between"] is True


def test_a_set_without_between_serialises_with_no_between_key():
    library = load_library(ROOT / "docs" / "tutorial-set")
    for symbol in library.symbols.values():
        assert all("between" not in e for e in symbol_to_data(symbol)["elements"]), symbol.name


def test_between_round_trips_through_resolved_data():
    assert round_trips(ticked())


def toml_symbol(element: str) -> str:
    """A minimal symbol file whose only element is the given TOML lines."""
    return (
        'schema = 1\nname = "x"\nkind = "symbol"\nstatus = "unverified"\nslots = {}\n'
        '[reference]\nstandard = "Example set"\nnumber = "sym-a"\n'
        f"[[elements]]\n{element}\n"
    )


@pytest.mark.parametrize(
    "element",
    [
        "line = [[0, 0], [1, 0]]\nbetween = true",
        "polyline = [[0, 0], [1, 0], [1, 1]]\nbetween = true",
    ],
)
def test_between_loads_on_a_line_and_a_polyline(element):
    data, findings = parse_toml(toml_symbol(element))
    assert findings == ()
    assert data is not None
    assert validate(data) == ()
    assert len(betweens(symbol_from_data(data))) == 1


@pytest.mark.parametrize(
    "element",
    [
        "circle = [0, 0]\nr = 1\nbetween = true",
        "arc = [0, 0]\nr = 1\nstart = 0\nend = 90\nbetween = true",
        'text = "a"\nat = [0, 0]\nheight = 1\nbetween = true',
    ],
)
def test_between_is_a_finding_on_a_circle_an_arc_and_a_text(element):
    data, _ = parse_toml(toml_symbol(element))
    assert {f.location for f in validate(data)} == {"/elements/0/between"}


@pytest.mark.parametrize(
    ("element", "accepted"),
    [
        ("line = [[0, 0], [1, 0]]\nbetween = true", True),
        ("polyline = [[0, 0], [1, 0]]\nbetween = true", True),
        ("line = [[0, 0], [1, 0]]\nbetween = 1", False),
        ("circle = [0, 0]\nr = 1\nbetween = true", False),
    ],
)
def test_the_json_schema_agrees_with_the_loader_on_between(element, accepted):
    schema = json.loads(
        (ROOT / "src" / "symdef" / "schema" / "symbol.schema.json").read_text(encoding="utf-8")
    )
    data, _ = parse_toml(toml_symbol(element))
    assert Draft202012Validator(schema).is_valid(data) is accepted
    assert (validate(data) == ()) is accepted


def test_a_between_polyline_serialises_with_and_without_the_key():
    on = symbol_to_data(
        replace(row(), elements=(Polyline((Point(0, 0), Point(1, 0)), between=True),))
    )
    off = symbol_to_data(replace(row(), elements=(Polyline((Point(0, 0), Point(1, 0))),)))
    assert on["elements"][0]["between"] is True
    assert "between" not in off["elements"][0]
