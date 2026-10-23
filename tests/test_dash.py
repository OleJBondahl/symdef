"""The `[dash]` table: parse, validate, the keys a style needs, bundle, `with_settings` (D115)."""

import json
import shutil
from pathlib import Path

import pytest
from test_build_load import CONFIG, GUIDE

from symdef.errors import InvalidValueError, LibraryError
from symdef.files import load_library
from symdef.geometry import Line, Point, Style, Weight
from symdef.load import library_from_bundle, parse_config, validate_bundle
from symdef.model import Library, Reference, Status, Symbol, SymbolKind, WireStyle
from symdef.serialize import bundle_to_data, to_json

DASHES = "[dash]\ndashed = [1.25, 0.625]\ndash_dot = [2.5, 0.625, 0.15625, 0.625]\nlong = [5, 1]\n"
WIRE = '[[wire]]\nid = "w"\nweight = "normal"\nstyle = "{}"\n'


def findings_of(extra: str) -> list[str]:
    parsed, findings = parse_config(CONFIG + extra)
    assert parsed is None
    return [f"{f.location}: {f.message}" for f in findings]


def guide_with(tmp_path: Path, dash: str) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(GUIDE, root)
    text = (GUIDE / "library.toml").read_text(encoding="utf-8")
    (root / "library.toml").write_text(text[: text.index("[dash]")] + dash, encoding="utf-8")
    return root


def lib(dash=None, style=Style.SOLID):
    line = Line(Point(0, 0), Point(1, 0), Weight.NORMAL, style)
    symbol = Symbol("t", SymbolKind.SYMBOL, Status.UNVERIFIED, Reference("X", "S1"), (line,))
    return Library("s", "s", "", {"S1": symbol}, dash=dash or {})


def test_the_table_parses_into_tuples_and_free_keys_are_data():
    parsed, findings = parse_config(CONFIG + DASHES)
    assert findings == ()
    assert parsed is not None
    assert dict(parsed.dash) == {
        "dashed": (1.25, 0.625),
        "dash_dot": (2.5, 0.625, 0.15625, 0.625),
        "long": (5, 1),
    }


def test_an_absent_or_empty_table_is_empty():
    for extra in ("", "[dash]\n"):
        parsed, findings = parse_config(CONFIG + extra)
        assert findings == ()
        assert parsed is not None
        assert dict(parsed.dash) == {}


@pytest.mark.parametrize(
    ("extra", "location", "fragment"),
    [
        ("[dash]\nlong = [1, 2, 3]\n", "/dash/long", "even number"),
        ("[dash]\nlong = []\n", "/dash/long", "even number"),
        ("[dash]\ndashed = [1, 2, 3, 4]\n", "/dash/dashed", "exactly 2"),
        ("[dash]\ndash_dot = [1, 2]\n", "/dash/dash_dot", "exactly 4"),
        ("[dash]\nlong = [1, 0]\n", "/dash/long/1", "above zero"),
        ("[dash]\nlong = [1, 'x']\n", "/dash/long/1", "number"),
        ("[dash]\nlong = 3\n", "/dash/long", "array"),
    ],
)
def test_a_bad_table_is_a_finding_at_its_name(extra, location, fragment):
    messages = findings_of(extra)
    assert any(m.startswith(location + ": ") and fragment in m for m in messages), messages


def test_a_dash_that_is_not_a_table_is_a_finding():
    parsed, findings = parse_config("dash = 3\n" + CONFIG)
    assert parsed is None
    assert [(f.location, f.message) for f in findings] == [("/dash", "must be a table")]


def test_the_mapping_is_read_only():
    parsed, _ = parse_config(CONFIG + DASHES)
    assert parsed is not None
    with pytest.raises(TypeError):
        parsed.dash["dashed"] = (1, 1)  # ty: ignore[invalid-assignment] - proves it is read-only


def test_load_library_carries_the_patterns():
    assert load_library(GUIDE).dash["dashed"] == (1.25, 0.625)


def test_a_symbol_in_a_style_without_its_pattern_fails_the_load_naming_the_key(tmp_path):
    with pytest.raises(LibraryError, match=r"'dashed'.*no 'dashed'"):
        load_library(guide_with(tmp_path, "[dash]\ndash_dot = [2, 1, 0.1, 1]\n"))


def test_a_wire_style_without_its_pattern_fails_the_load_naming_the_key(tmp_path):
    root = tmp_path / "pipe"
    shutil.copytree(Path(GUIDE).parent / "pipe", root)
    (root / "library.toml").write_text(
        (root / "library.toml").read_text(encoding="utf-8") + WIRE.format("dash_dot")
    )
    with pytest.raises(LibraryError, match="no 'dash_dot'"):
        load_library(root)
    (root / "library.toml").write_text(
        (root / "library.toml").read_text(encoding="utf-8") + "[dash]\ndash_dot = [2, 1, 0.1, 1]\n"
    )
    assert load_library(root).dash["dash_dot"] == (2, 1, 0.1, 1)


def test_an_empty_table_is_legal_when_nothing_is_dashed(tmp_path):
    root = tmp_path / "pipe"
    shutil.copytree(Path(GUIDE).parent / "pipe", root)
    (root / "library.toml").write_text(
        (root / "library.toml").read_text(encoding="utf-8") + "[dash]\n"
    )
    assert dict(load_library(root).dash) == {}


def test_the_bundle_round_trips_the_patterns_sorted():
    data = json.loads(to_json(bundle_to_data(lib({"long": (5, 1), "dashed": [1, 2]}))))
    assert data["dash"] == {"dashed": [1, 2], "long": [5, 1]}
    assert validate_bundle(data) == ()
    assert library_from_bundle(data).dash == {"dashed": (1, 2), "long": (5, 1)}


def test_a_library_without_patterns_writes_no_dash_key():
    assert "dash" not in bundle_to_data(lib())


def test_a_bad_dash_object_in_a_bundle_is_invalid():
    data = json.loads(to_json(bundle_to_data(lib())))
    data["dash"] = {"dashed": [1, 2, 3]}
    (finding,) = validate_bundle(data)
    assert finding.location == "/dash/dashed"


def test_a_bundle_whose_symbols_need_a_pattern_it_lacks_is_invalid():
    data = json.loads(to_json(bundle_to_data(lib(style=Style.DASH_DOT))))
    (finding,) = validate_bundle(data)
    assert finding.location == "/dash"
    assert "'dash_dot'" in finding.message
    data["wires"] = [{"id": "w", "weight": "rule", "style": "dashed"}]
    assert len(validate_bundle(data)) == 2  # dashed (the wire) and dash_dot (the line)


def test_the_library_copies_its_patterns_into_a_read_only_mapping():
    source = {"dashed": [1, 2]}
    library = lib(source)
    source["dashed"].append(3)
    assert library.dash["dashed"] == (1, 2)
    with pytest.raises(TypeError):
        library.dash["x"] = (1, 1)


def test_with_settings_replaces_the_whole_table_and_none_keeps_it():
    base = lib({"dashed": (1, 2), "long": (5, 1)}, Style.DASHED)
    assert base.with_settings().dash == base.dash
    result = base.with_settings(dash={"dashed": [3, 1]})
    assert dict(result.dash) == {"dashed": (3, 1)}
    assert dict(base.dash) == {"dashed": (1, 2), "long": (5, 1)}


def test_with_settings_sets_lines_and_dash_in_one_call():
    base = lib({"dashed": (1, 2)}, Style.DASHED)
    result = base.with_settings(
        lines={Weight.NORMAL: 0.3, Weight.RULE: 0.18}, dash={"dashed": (2, 2)}
    )
    assert result.lines == {Weight.NORMAL: 0.3, Weight.RULE: 0.18}
    assert result.dash["dashed"] == (2, 2)


@pytest.mark.parametrize(
    ("bad", "fragment"),
    [
        (3, "not a mapping"),
        ({1: [1, 2]}, "not a mapping"),
        ({"dashed": 3}, "not a list"),
        ({"dashed": "ab"}, "not a list"),
        ({"dashed": [1, 2, 3]}, "exactly 2"),
        ({"dashed": [1, 0]}, "above zero"),
        ({"dashed": [1, "x"]}, "not a number"),
        ({"long": [1]}, "even number"),
        ({"long": [1, 2]}, "'dashed'"),
    ],
)
def test_with_settings_rejects_a_bad_table(bad, fragment):
    with pytest.raises(InvalidValueError, match=fragment):
        lib({"dashed": (1, 2)}, Style.DASHED).with_settings(dash=bad)


def test_with_settings_rejects_a_table_missing_a_pattern_a_wire_uses():
    base = Library("s", "s", "", {}, wires=(WireStyle("w", Weight.RULE, Style.DASH_DOT),))
    with pytest.raises(InvalidValueError, match="'dash_dot'"):
        base.with_settings(dash={"dashed": (1, 2)})
