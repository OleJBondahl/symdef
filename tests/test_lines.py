"""The `[lines]` table: parse, validate, expose on `Library`, round-trip through the bundle."""

import json
from pathlib import Path

import pytest
from neutral_font import NEUTRAL_FONT
from test_build_load import CONFIG, data_repo

from symdef.errors import LibraryError
from symdef.files import load_library
from symdef.geometry import TEXT_WEIGHTS, Style, Weight
from symdef.lines import lines_problems
from symdef.load import library_from_bundle, parse_config, validate_bundle
from symdef.model import Library, WireStyle
from symdef.serialize import bundle_to_data, to_json

WIRE = '[[wire]]\nid = "w"\nweight = "{}"\nstyle = "solid"\n'
HOUSE = "[lines]\nnormal = 0.25\nthick = 0.5\n"


def config(extra: str) -> str:
    return CONFIG + extra


def findings_of(extra: str) -> list[str]:
    parsed, findings = parse_config(config(extra))
    assert parsed is None
    return [f"{f.location}: {f.message}" for f in findings]


def test_the_table_parses_into_weights():
    parsed, findings = parse_config(config(HOUSE + WIRE.format("thick")))
    assert findings == ()
    assert parsed is not None
    assert dict(parsed.lines) == {Weight.NORMAL: 0.25, Weight.THICK: 0.5}


def test_an_absent_table_is_empty_and_nothing_is_checked():
    parsed, findings = parse_config(config(WIRE.format("thick")))
    assert findings == ()
    assert parsed is not None
    assert dict(parsed.lines) == {}


def test_the_mapping_is_read_only():
    parsed, _ = parse_config(config(HOUSE))
    assert parsed is not None
    with pytest.raises(TypeError):
        parsed.lines[Weight.NORMAL] = 1.0  # ty: ignore[invalid-assignment] - proves it is read-only


def test_a_wire_weight_without_a_width_is_a_finding_naming_it():
    (message,) = findings_of("[lines]\nnormal = 0.25\n" + WIRE.format("thick"))
    assert message.startswith("/lines: ")
    assert "'thick'" in message
    assert "[lines]" in message


def test_an_unknown_weight_name_is_a_finding_naming_the_valid_ones():
    (message,) = findings_of("[lines]\nbold = 1\n")
    assert message.startswith("/lines/bold: ")
    assert "'normal'" in message
    assert "'thick'" in message


@pytest.mark.parametrize("value", ["0", "-0.25", '"0.25"', "true"])
def test_a_width_that_is_not_a_number_above_zero_is_a_finding(value):
    (message,) = findings_of(f"[lines]\nnormal = {value}\n")
    assert message.startswith("/lines/normal: ")


def test_load_library_raises_a_library_error_for_a_missing_width(tmp_path):
    root = data_repo(tmp_path, config("[lines]\nnormal = 0.25\n" + WIRE.format("thick")))
    with pytest.raises(LibraryError) as raised:
        load_library(root)
    assert any("'thick'" in f.message for f in raised.value.findings)


def test_load_library_carries_the_widths(tmp_path):
    library = load_library(data_repo(tmp_path, config(HOUSE)))
    assert dict(library.lines) == {Weight.NORMAL: 0.25, Weight.THICK: 0.5}


def test_lines_problems_names_each_missing_weight_once():
    wires = (
        WireStyle("a", Weight.THICK, Style.SOLID),
        WireStyle("b", Weight.THICK, Style.SOLID),
        WireStyle("c", Weight.NORMAL, Style.SOLID),
    )
    assert lines_problems(wires, {}) == ()
    assert lines_problems(wires, {Weight.NORMAL: 0.25, Weight.THICK: 0.5}) == ()
    (message,) = lines_problems(wires, {Weight.NORMAL: 0.25})
    assert "'thick'" in message


def bare(lines) -> Library:
    return Library("S", "S", "", {}, lines=lines, font=NEUTRAL_FONT, port_format="{k}.{port}")


def test_the_bundle_round_trips_the_widths():
    data = json.loads(to_json(bundle_to_data(bare({Weight.THICK: 0.5, Weight.NORMAL: 0.25}))))
    assert data["lines"] == {"normal": 0.25, "thick": 0.5}
    assert validate_bundle(data) == ()
    assert library_from_bundle(data).lines == {Weight.NORMAL: 0.25, Weight.THICK: 0.5}


def test_a_bundle_with_a_bad_lines_object_is_invalid():
    data = json.loads(to_json(bundle_to_data(bare({}))))
    data["lines"] = {"bold": 1, "normal": -1}
    assert len(validate_bundle(data)) == 2


def test_a_library_without_widths_writes_no_lines_key():
    assert "lines" not in bundle_to_data(bare({}))
    assert "lines" not in bundle_to_data(load_library(Path(__file__).parent / "fixtures" / "guide"))


def test_rule_is_a_weight_of_lines_and_wire_styles():
    parsed, findings = parse_config(config("[lines]\nrule = 0.18\n" + WIRE.format("rule")))
    assert findings == ()
    assert parsed is not None
    assert dict(parsed.lines) == {Weight.RULE: 0.18}
    assert parsed.wires[0].weight is Weight.RULE


def test_a_rule_wire_without_a_rule_width_is_a_finding_naming_it():
    (message,) = findings_of("[lines]\nnormal = 0.25\n" + WIRE.format("rule"))
    assert "'rule'" in message


def test_rule_is_not_a_weight_of_a_symbol_element():
    from symdef.load import validate

    data = {"line": [[0, 0], [1, 0]], "weight": "rule"}
    findings = validate({"elements": [data]})
    assert any(f.location == "/elements/0/weight" for f in findings)


def test_text_weights_are_normal_and_thick_never_rule():
    assert TEXT_WEIGHTS == (Weight.NORMAL, Weight.THICK)
