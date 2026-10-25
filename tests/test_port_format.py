"""`port_format`: the library-wide template of a repeated pole's port id (D123)."""

import shutil
from pathlib import Path

import pytest
from test_resolve import composite

from symdef.errors import LibraryError
from symdef.files import load_library
from symdef.load import library_from_bundle, parse_config, validate_bundle
from symdef.serialize import bundle_to_data

GUIDE = Path(__file__).resolve().parent / "fixtures" / "guide"
KEY = 'port_format = "{k}.{port}"\n'
PLAIN = (GUIDE / "library.toml").read_text(encoding="utf-8").replace(KEY, "")
TOP = composite(
    "sym-z-094",
    'parts = [{ as = "a", use = "make-contact", repeat = 2 }]\n'
    'ports = { "1.in" = "a.1.in", "1.out" = "a.1.out", "2.in" = "a.2.in", "2.out" = "a.2.out" }\n',
)


def tree(tmp_path, key=""):
    root = tmp_path / "lib"
    shutil.copytree(GUIDE, root)
    (root / "symbols" / "sym-z-094.toml").write_text(TOP, encoding="utf-8")
    (root / "library.toml").write_text(key + PLAIN, encoding="utf-8")
    return root


def test_library_toml_declares_the_format():
    config, findings = parse_config(PLAIN.replace("\n[", '\nport_format = "P{k}_{port}"\n[', 1))
    assert findings == ()
    assert config is not None
    assert config.port_format == "P{k}_{port}"


def test_a_library_toml_without_the_key_is_refused_with_the_key_and_the_fix():
    config, findings = parse_config(PLAIN)
    assert config is None
    (found,) = findings
    assert "missing required key 'port_format'" in found.message
    assert "add port_format to library.toml" in found.message


@pytest.mark.parametrize("bad", ['"{k}"', '"plain"', "3", '"{k}.{port"'])
def test_a_bad_format_is_a_finding_at_the_key(bad):
    text = PLAIN.replace("\n[", f"\nport_format = {bad}\n[", 1)
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
    assert [p.id for p in library.get("sym-z-094").ports] == ["1.in", "1.out", "2.in", "2.out"]


def test_the_library_and_its_bundle_carry_the_format():
    library = load_library(GUIDE)
    assert library.port_format == "{k}.{port}"
    data = bundle_to_data(library)
    assert data["port_format"] == "{k}.{port}"
    assert validate_bundle(data) == ()
    assert library_from_bundle(data).port_format == "{k}.{port}"
    assert (
        library_from_bundle({k: v for k, v in data.items() if k != "port_format"}).port_format
        is None
    )
    assert validate_bundle({**data, "port_format": "{k}"})[0].location == "/port_format"
