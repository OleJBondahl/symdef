"""`port_format`: the library-wide template of a repeated pole's port id (D123)."""

import shutil
from pathlib import Path

import pytest
from test_resolve import composite

from symdef.errors import LibraryError
from symdef.files import load_library
from symdef.load import parse_config

GUIDE = Path(__file__).resolve().parent / "fixtures" / "guide"
TOP = composite(
    "S00094",
    'parts = [{ as = "a", use = "S00227", repeat = 2 }]\n'
    'ports = { "1.in" = "a.1.in", "1.out" = "a.1.out", "2.in" = "a.2.in", "2.out" = "a.2.out" }\n',
)


def tree(tmp_path, key=""):
    root = tmp_path / "lib"
    shutil.copytree(GUIDE, root)
    (root / "symbols" / "S00094.toml").write_text(TOP, encoding="utf-8")
    text = (root / "library.toml").read_text(encoding="utf-8")
    (root / "library.toml").write_text(key + text, encoding="utf-8")
    return root


def test_library_toml_declares_the_format():
    config, findings = parse_config(
        (GUIDE / "library.toml")
        .read_text(encoding="utf-8")
        .replace("\n[", '\nport_format = "P{k}_{port}"\n[', 1)
    )
    assert findings == ()
    assert config is not None
    assert config.port_format == "P{k}_{port}"
    plain, _ = parse_config((GUIDE / "library.toml").read_text(encoding="utf-8"))
    assert plain is not None
    assert plain.port_format is None


@pytest.mark.parametrize("bad", ['"{k}"', '"plain"', "3", '"{k}.{port"'])
def test_a_bad_format_is_a_finding_at_the_key(bad):
    text = (
        (GUIDE / "library.toml")
        .read_text(encoding="utf-8")
        .replace("\n[", f"\nport_format = {bad}\n[", 1)
    )
    config, findings = parse_config(text)
    assert config is None
    assert [f.location for f in findings] == ["/port_format"]
    assert "port_format" in findings[0].message


def test_a_library_that_repeats_without_the_key_fails_to_load_naming_the_key(tmp_path):
    with pytest.raises(LibraryError) as raised:
        load_library(tree(tmp_path))
    message = str(raised.value)
    assert "port_format" in message
    assert "library.toml" in message


def test_with_the_key_the_library_loads_and_the_ports_follow_the_format(tmp_path):
    library = load_library(tree(tmp_path, 'port_format = "{k}.{port}"\n'))
    assert [p.id for p in library.get("S00094").ports] == ["1.in", "1.out", "2.in", "2.out"]
