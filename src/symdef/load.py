"""Read symbol files and `library.toml`: text or decoded data in, findings out, never raises.

`validate` is the hand-written twin of `schema/symbol.schema.json` (in the package); the agreement
test keeps the two in step. Both are structural only: types, required keys, enums and array shapes.
The id pattern, the grid, positive sizes and the number pattern are lint rules. The one bound on
values is that every number is finite with an absolute value of at most 1e6 module units, which
keeps all later arithmetic total.
"""

import json
import re
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import replace
from types import MappingProxyType
from typing import Any

from symdef.font import FontMetrics
from symdef.geometry import (
    Arc,
    Box,
    Circle,
    Direction,
    Element,
    Fill,
    Line,
    Point,
    Polyline,
    Style,
    Text,
    Weight,
)
from symdef.lines import lines_problems
from symdef.model import (
    Allow,
    Anchor,
    Centre,
    Finding,
    Library,
    LibraryConfig,
    Node,
    Path,
    Port,
    Reference,
    Severity,
    Slot,
    Status,
    Stretch,
    Symbol,
    SymbolKind,
    Vocabulary,
    WireStyle,
)
from symdef.units import (
    DEFAULT_GRID,
    DEFAULT_WIRE_PITCH,
    DEFAULT_WIRE_PITCH_FINE,
    Grid,
    divisions_error,
    module_error,
    pitch_error,
)

# Every number in a file is finite with an absolute value of at most this (1e6 M is 2.5 km).
_LIMIT = 1_000_000

# A check takes a decoded value and its JSON-pointer-like location ("" is the root) and returns
# the violations it finds.
_Check = Callable[[object, str], list[Finding]]


def _finding(location: str, message: str) -> Finding:
    """Make a `schema` error; the root location becomes `None`."""
    return Finding("schema", Severity.ERROR, message, location or None)


def _short(text: object, limit: int = 60) -> str:
    """Cap text that comes from the input, so a finding stays readable whatever it was fed.

    A mapping key that is not a string is shown as `str` shows it.
    """
    shown = str(text)
    return shown if len(shown) <= limit else shown[:limit] + "..."


def _child(location: str, key: str | int) -> str:
    """Extend a location by one key, escaping `~` and `/` as JSON Pointer does."""
    escaped = str(key).replace("~", "~0").replace("/", "~1")
    return f"{location}/{escaped}"


def _is_number(value: object) -> bool:
    """Return whether a value is a JSON number: an int or float, never a bool."""
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_integer(value: object) -> bool:
    """Return whether a value is a JSON integer; like JSON Schema, `8.0` counts."""
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or (isinstance(value, float) and value.is_integer())


def _string(value: object, location: str) -> list[Finding]:
    """Check for a string."""
    return [] if isinstance(value, str) else [_finding(location, "must be a string")]


def _within_limit(value: object) -> bool:
    """Return whether a number is at most `_LIMIT` in absolute value; NaN and infinity are not."""
    return isinstance(value, int | float) and -_LIMIT <= value <= _LIMIT


def _number(value: object, location: str) -> list[Finding]:
    """Check for a number within the limit."""
    if not _is_number(value):
        return [_finding(location, "must be a number")]
    if not _within_limit(value):
        return [_finding(location, f"must be a number between -{_LIMIT} and {_LIMIT}")]
    return []


def _integer(value: object, location: str) -> list[Finding]:
    """Check for an integer within the limit."""
    if not _is_integer(value):
        return [_finding(location, "must be an integer")]
    if not _within_limit(value):
        return [_finding(location, f"must be an integer between -{_LIMIT} and {_LIMIT}")]
    return []


def _positive(value: object, location: str) -> list[Finding]:
    """Check for a number within the limit that is above zero."""
    found = _number(value, location)
    if not found and value <= 0:  # ty: ignore[unsupported-operator] - _number proved a number
        return [_finding(location, "must be above zero")]
    return found


def _boolean(value: object, location: str) -> list[Finding]:
    """Check for a boolean."""
    return [] if isinstance(value, bool) else [_finding(location, "must be true or false")]


def _schema_version(value: object, location: str) -> list[Finding]:
    """Check that the schema version is 1."""
    return [] if _is_number(value) and value == 1 else [_finding(location, "must be 1")]


def _enum(*allowed: str) -> _Check:
    """Build a check for one of a fixed set of strings."""

    def check(value: object, location: str) -> list[Finding]:
        if isinstance(value, str) and value in allowed:
            return []
        return [_finding(location, f"must be one of {', '.join(allowed)}")]

    return check


def _array(item: _Check, length: int | None = None) -> _Check:
    """Build a check for an array whose items pass `item`, optionally of an exact length."""

    def check(value: object, location: str) -> list[Finding]:
        if not isinstance(value, list):
            return [_finding(location, "must be an array")]
        found = []
        if length is not None and len(value) != length:
            found.append(_finding(location, f"must have exactly {length} items"))
        for index, entry in enumerate(value):
            found += item(entry, _child(location, index))
        return found

    return check


def _table(fields: Mapping[str, _Check], required: tuple[str, ...] = ()) -> _Check:
    """Build a check for a table with these keys and no others."""

    def check(value: object, location: str) -> list[Finding]:
        if not isinstance(value, dict):
            return [_finding(location, "must be a table")]
        found = [
            _finding(location, f"missing required key {key!r}")
            for key in required
            if key not in value
        ]
        for key, entry in value.items():
            if key in fields:
                found += fields[key](entry, _child(location, key))
            else:
                found.append(_finding(_child(location, key), f"unknown key {_short(key)!r}"))
        return found

    return check


def _map_of(item: _Check) -> _Check:
    """Build a check for a table with any keys whose values pass `item`."""

    def check(value: object, location: str) -> list[Finding]:
        if not isinstance(value, dict):
            return [_finding(location, "must be a table")]
        found = []
        for key, entry in value.items():
            found += item(entry, _child(location, key))
        return found

    return check


_POINT = _array(_number, 2)
_BOX = _array(_POINT, 2)
_DECLARED_BOX = _array(_number, 4)
_DIRECTION = _enum("N", "E", "S", "W")
_SLOT_SIDE = _enum("N", "E", "S", "W", "C")
_WEIGHT = _enum("normal", "thick")
_STYLE = _enum("solid", "dashed", "dash_dot")
_FILL = _enum("none", "solid")
_POLYLINE_FILL = _enum("none", "solid", "tint")

_REFERENCE = _table(
    {"standard": _string, "number": _string, "edition": _string, "form": _string},
    required=("standard", "number"),
)
_PORT = _table(
    {
        "id": _string,
        "at": _POINT,
        "dir": _DIRECTION,
        "description": _string,
        "pattern": _boolean,
    },
    required=("id", "at", "dir"),
)
_NODE = _table(
    {
        "ports": _array(_string),
        "potential": _string,
    },
    required=("ports",),
)
_PATH = _table(
    {
        "from": _string,
        "to": _string,
        "kind": _string,
        "through": _boolean,
    },
    required=("from", "to", "kind"),
)
_ANCHOR = _table({"id": _string, "at": _POINT, "dir": _DIRECTION}, required=("id", "at", "dir"))
_SLOT = _table(
    {"at": _POINT, "side": _SLOT_SIDE, "box": _array(_number, 2), "turn": _boolean},
    required=("at", "side", "box"),
)
_PART = _table(
    {
        "as": _string,
        "use": _string,
        "orient": _enum("R0", "R90", "R180", "R270", "MR0", "MR90", "MR180", "MR270"),
        "attach": _string,
        "to": _string,
        "length": _number,
        "via": _string,
        "at": _POINT,
        "repeat": _integer,
    },
    required=("as", "use"),
)
_ALLOW = _table({"rule": _string, "reason": _string}, required=("rule", "reason"))
_STRETCH = _table(
    {"axis": _enum("x", "y"), "at": _number, "weight": _positive}, required=("axis", "at")
)

_POLYLINE = _table(
    {
        "polyline": _array(_POINT),
        "closed": _boolean,
        "fill": _POLYLINE_FILL,
        "weight": _WEIGHT,
        "style": _STYLE,
        "between": _boolean,
    },
    required=("polyline",),
)


def _polyline(value: dict[str, Any], location: str) -> list[Finding]:
    """Check a polyline; a tint fill is only for a closed one."""
    found = _POLYLINE(value, location)
    if value.get("fill") == "tint" and value.get("closed") is not True:
        found.append(_finding(_child(location, "fill"), "tint fill needs a closed polyline"))
    return found


# One table per shape, keyed by the shape key; an element has exactly one of these keys.
_ELEMENTS = {
    "line": _table(
        {
            "line": _array(_POINT, 2),
            "weight": _WEIGHT,
            "style": _STYLE,
            "port": _string,
            "between": _boolean,
        },
        required=("line",),
    ),
    "polyline": _polyline,
    "circle": _table(
        {"circle": _POINT, "r": _number, "fill": _FILL, "weight": _WEIGHT},
        required=("circle", "r"),
    ),
    "arc": _table(
        {
            "arc": _POINT,
            "r": _number,
            "start": _number,
            "end": _number,
            "weight": _WEIGHT,
            "style": _STYLE,
        },
        required=("arc", "r", "start", "end"),
    ),
    "text": _table(
        {"text": _string, "at": _POINT, "height": _number, "weight": _WEIGHT},
        required=("text", "at", "height"),
    ),
}


def _element(value: object, location: str) -> list[Finding]:
    """Check an element: a table with exactly one shape key and only that shape's other keys."""
    if not isinstance(value, dict):
        return [_finding(location, "must be a table")]
    shapes = [key for key in value if key in _ELEMENTS]
    if len(shapes) != 1:
        return [
            _finding(
                location,
                "an element needs exactly one shape key: line, polyline, circle, arc or text",
            )
        ]
    return _ELEMENTS[shapes[0]](value, location)


def _ports(value: object, location: str) -> list[Finding]:
    """Check `ports`: an array of port tables (atomic) or a table of strings (composite)."""
    if isinstance(value, list):
        return _array(_PORT)(value, location)
    if isinstance(value, dict):
        return _map_of(_string)(value, location)
    return [_finding(location, "must be an array of tables, or a table of strings in a composite")]


def _slot(value: object, location: str) -> list[Finding]:
    """Check one slot: a table, or in a composite a string reference to a part's slot."""
    return [] if isinstance(value, str) else _SLOT(value, location)


_FILE = _table(
    {
        "schema": _schema_version,
        "name": _string,
        "kind": _enum("symbol", "element", "qualifier"),
        "status": _enum("unverified", "verified"),
        "reference": _REFERENCE,
        "ports": _ports,
        "nodes": _array(_NODE),
        "paths": _array(_PATH),
        "anchors": _array(_ANCHOR),
        "elements": _array(_element),
        "parts": _array(_PART),
        "slots": _map_of(_slot),
        "pole_pitch": _integer,
        "lint_allow": _array(_ALLOW),
        "stretch": _array(_STRETCH),
        "body": _DECLARED_BOX,
        "keepout": _DECLARED_BOX,
        "body_box": _BOX,
        "keepout_box": _BOX,
    },
    required=("schema", "name", "kind", "status", "reference"),
)


def parse_toml(text: str) -> tuple[dict[str, Any] | None, tuple[Finding, ...]]:
    """Decode TOML text; input the parser rejects or cannot handle becomes a `schema` finding.

    `TOMLDecodeError` is a `ValueError`, as is the error for an integer of more than 4300 digits;
    absurdly deep nesting exhausts the stack instead.
    """
    try:
        data = tomllib.loads(text)
    except (ValueError, RecursionError) as error:
        return None, (_finding("", _short(f"invalid TOML: {error}", 200)),)
    return data, ()


def _declared_order(data: Mapping[str, Any]) -> list[Finding]:
    """Check that each well-formed declared box runs from its low corner to its high corner."""
    found = []
    for key in ("body", "keepout"):
        if key not in data:
            continue
        box = data[key]
        if not _DECLARED_BOX(box, key) and not (box[0] < box[2] and box[1] < box[3]):
            found.append(
                _finding(
                    _child("", key),
                    f"symbol {_short(data.get('name'))!r}: {key} = [x0, y0, x1, y1] needs x0 < x1 "
                    f"and y0 < y1; write the low corner first and give the box a size",
                )
            )
    return found


def validate(data: object) -> tuple[Finding, ...]:
    """Check decoded data against the symbol file format, atomic, composite or resolved.

    Args:
        data: A decoded TOML or JSON document.

    Returns:
        One `schema` error per violation, located by a JSON-pointer-like path (`/ports/0/dir`;
        `None` for the whole file). Empty when the data is acceptable to the JSON Schema.
    """
    found = _FILE(data, "")
    if isinstance(data, dict):
        found += _declared_order(data)
        if "elements" not in data and "parts" not in data:
            found.append(_finding("", "a file needs elements, parts, or both"))
        if data.get("kind") == "symbol" and "slots" not in data:
            found.append(
                _finding("", "missing required key 'slots' (required when kind is symbol)")
            )
    return tuple(found)


def parse_json(text: str) -> tuple[Any, tuple[Finding, ...]]:
    """Decode JSON text; input the parser rejects or cannot handle becomes a `schema` finding.

    Like `parse_toml`, `ValueError` covers a syntax error and an integer of more than 4300
    digits; absurdly deep nesting exhausts the stack instead. The data is `None` on a finding
    (and also when the text is the JSON `null`, which `validate_bundle` then rejects).
    """
    try:
        return json.loads(text), ()
    except (ValueError, RecursionError) as error:
        return None, (_finding("", _short(f"invalid JSON: {error}", 200)),)


def _point(value: list[float]) -> Point:
    """Build a point from an `[x, y]` array."""
    return Point(value[0], value[1])


def _element_from_data(item: Mapping[str, Any]) -> Element:
    """Build an element, filling in the documented defaults for absent keys."""
    weight = Weight[item.get("weight", "normal").upper()]
    if "line" in item:
        start, end = item["line"]
        return Line(
            _point(start),
            _point(end),
            weight,
            Style(item.get("style", "solid")),
            item.get("port"),
            between=item.get("between", False),
        )
    if "polyline" in item:
        return Polyline(
            tuple(_point(p) for p in item["polyline"]),
            item.get("closed", False),
            Fill(item.get("fill", "none")),
            weight,
            Style(item.get("style", "solid")),
            between=item.get("between", False),
        )
    if "circle" in item:
        return Circle(_point(item["circle"]), item["r"], Fill(item.get("fill", "none")), weight)
    if "arc" in item:
        return Arc(
            _point(item["arc"]),
            item["r"],
            item["start"],
            item["end"],
            weight,
            Style(item.get("style", "solid")),
        )
    return Text(item["text"], _point(item["at"]), item["height"], weight)


def _declared_box(value: list[float] | None) -> Box | None:
    """Build a declared box from `[x0, y0, x1, y1]`, or None when the key is absent."""
    if value is None:
        return None
    return Box(Point(value[0], value[1]), Point(value[2], value[3]))


def symbol_from_data(data: Mapping[str, Any]) -> Symbol:
    """Build a symbol from validated atomic data: a TOML file or a resolved JSON symbol.

    Absent optional keys take their documented defaults, so the explicit keys of the resolved
    form read the same way. `schema`, `body_box` and `keepout_box` are ignored; `body` and
    `keepout` declare the boxes (D98). Slots keep their table order. Composite-only forms
    (`parts`, a rename-map `ports`, string slot references) are the resolver's business.

    Args:
        data: Decoded data for which `validate` returned no findings.

    Returns:
        The symbol.
    """
    reference = data["reference"]
    ports = data.get("ports")
    return Symbol(
        name=data["name"],
        kind=SymbolKind(data["kind"]),
        status=Status(data["status"]),
        reference=Reference(
            reference["standard"],
            reference["number"],
            reference.get("edition"),
            reference.get("form"),
        ),
        elements=tuple(_element_from_data(e) for e in data.get("elements", ())),
        ports=tuple(
            Port(
                p["id"],
                _point(p["at"]),
                Direction[p["dir"]],
                p.get("description", ""),
                p.get("pattern", False),
            )
            for p in (ports if isinstance(ports, list) else ())
        ),
        nodes=tuple(Node(tuple(n["ports"]), n.get("potential")) for n in data.get("nodes", ())),
        paths=tuple(
            Path(p["from"], p["to"], p["kind"], p.get("through", False))
            for p in data.get("paths", ())
        ),
        anchors=tuple(
            Anchor(a["id"], _point(a["at"]), Direction[a["dir"]]) for a in data.get("anchors", ())
        ),
        slots=tuple(
            Slot(
                key,
                _point(s["at"]),
                Centre.C if s["side"] == "C" else Direction[s["side"]],
                (s["box"][0], s["box"][1]),
                s.get("turn", False),
            )
            for key, s in data.get("slots", {}).items()
            if isinstance(s, dict)
        ),
        pole_pitch=int(data["pole_pitch"]) if "pole_pitch" in data else None,
        lint_allow=tuple(Allow(a["rule"], a["reason"]) for a in data.get("lint_allow", ())),
        stretch=tuple(
            Stretch(s["axis"], s["at"], s.get("weight", 1)) for s in data.get("stretch", ())
        ),
        body=_declared_box(data.get("body")),
        keepout=_declared_box(data.get("keepout")),
    )


# A number is a file stem (`5.1.toml`, `ISO-14617-1.1.toml`) and `write_build` names files after
# it: letters, digits, `_` and `-`, in parts joined by single dots, so no separator, no `..`.
_PACKAGE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_STEM = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*")


def is_file_stem(text: object) -> bool:
    """Return whether a reference number is safe to use as a file name in a build.

    Anything that is not a string is not.
    """
    return isinstance(text, str) and _STEM.fullmatch(text) is not None


def _bundle_symbol(value: object, location: str) -> list[Finding]:
    """Check one bundle symbol: `validate` and the resolved form (no `parts`, arrays, tables)."""
    found = [replace(f, location=location + (f.location or "")) for f in validate(value)]
    if not isinstance(value, dict):
        return found
    if "parts" in value:
        found.append(_finding(_child(location, "parts"), "a bundle symbol has no parts"))
    if "ports" in value and not isinstance(value["ports"], list):
        found.append(_finding(_child(location, "ports"), "must be an array in a bundle"))
    slots = value.get("slots")
    if isinstance(slots, dict):
        found.extend(
            _finding(_child(_child(location, "slots"), key), "must be a table in a bundle")
            for key, slot in slots.items()
            if isinstance(slot, str)
        )
    return found


_WIRE = _table(
    {
        "id": _string,
        "weight": _enum(*(w.name.lower() for w in Weight)),
        "style": _enum(*(s.value for s in Style)),
    },
    required=("id", "weight", "style"),
)


def _wires(value: object, location: str) -> list[Finding]:
    """Check a list of wire styles: each one a `_WIRE` table, and no id given twice."""
    found = _array(_WIRE)(value, location)
    if isinstance(value, list):
        ids = [e.get("id") for e in value if isinstance(e, dict)]
        for wire_id in sorted({i for i in ids if isinstance(i, str) and ids.count(i) > 1}):
            found.append(_finding(location, f"duplicate wire id {_short(wire_id)!r}"))
    return found


def _wires_from_data(entries: list[dict[str, str]]) -> tuple[WireStyle, ...]:
    """Build the wire styles of a checked `[[wire]]` list or a bundle's `wires` array."""
    return tuple(
        WireStyle(w["id"], Weight[w["weight"].upper()], Style(w["style"])) for w in entries
    )


def _advances(value: object, location: str) -> list[Finding]:
    """Check the `advances` table: a single character for each key, a number above zero for it."""
    found = _map_of(_positive)(value, location)
    if isinstance(value, dict):
        found += [
            _finding(_child(location, key), "must be a single character")
            for key in value
            if not (isinstance(key, str) and len(key) == 1)
        ]
    return found


_ADVANCE_TABLES = _table(
    {w.name.lower(): _advances for w in Weight}, required=tuple(w.name.lower() for w in Weight)
)
_TEXT_BLOCK = _enum("cap", "grid")
_FONT_FIELDS = ("units_per_em", "cap_height", "ascent", "descent", "default_advance")
_FONT = _table(
    {
        **dict.fromkeys(_FONT_FIELDS, _positive),
        "advances": _ADVANCE_TABLES,
        "heights": _map_of(_positive),
        "name": _string,
        "family": _string,
        "text_block": _TEXT_BLOCK,
    },
    required=(*_FONT_FIELDS, "advances", "name"),
)


def font_from_data(data: Mapping[str, Any]) -> FontMetrics:
    """Build the font metrics of a checked `[font]` table or a bundle's `font` object."""
    return FontMetrics(
        data["name"],
        data["units_per_em"],
        data["cap_height"],
        data["ascent"],
        data["descent"],
        {Weight[key.upper()]: dict(table) for key, table in data["advances"].items()},
        data["default_advance"],
        data.get("heights", {}),
        data.get("family", ""),
        data.get("text_block", "cap"),
    )


_FONT_FILES = _table(
    {
        "name": _string,
        "files": _table({"regular": _string, "bold": _string}, ("regular", "bold")),
        "heights": _map_of(_positive),
        "text_block": _TEXT_BLOCK,
    },
    required=("name", "files"),
)


def _font_table(value: object, location: str) -> list[Finding]:
    """Check `[font]`: the literal tables, or `name`, `files` and `heights`, not both."""
    if not isinstance(value, dict) or "files" not in value:
        return _FONT(value, location)
    if "family" in value:
        message = "`family` comes from the font file; remove it beside `files`"
        return [_finding(location, message)]
    extra = [key for key in value if key not in ("name", "files", "heights", "text_block")]
    if extra:
        message = (
            f"`{extra[0]}` is not a key of the files form (`name`, `files`, `heights`, "
            "`text_block`); remove it, or drop `files` and give the measured tables"
        )
        return [_finding(location, message)]
    return _FONT_FILES(value, location)


def _literal_font(data: Mapping[str, Any]) -> bool:
    """Whether a checked config has a `[font]` of the literal form."""
    return "font" in data and "files" not in data["font"]


def _font_files(
    data: Mapping[str, Any],
) -> tuple[tuple[str, str] | None, str, dict[str, float], str]:
    """Return the files form's paths, name, heights and text block of a checked `[font]`."""
    font = data.get("font", {})
    if "files" not in font:
        return None, "", {}, "cap"
    return (
        (font["files"]["regular"], font["files"]["bold"]),
        font["name"],
        dict(font.get("heights", {})),
        font.get("text_block", "cap"),
    )


def _module_mm(value: object, location: str) -> list[Finding]:
    """Check `module_mm` by the rule `Grid` itself applies, once it is a number."""
    found = _number(value, location)
    message = None if found else module_error(value)
    return found or ([_finding(location, message)] if message else [])


def _divisions(value: object, location: str) -> list[Finding]:
    """Check `divisions_per_module` by the rule `Grid` itself applies, once it is an integer."""
    found = _integer(value, location)
    message = None if found else divisions_error(int(value))  # ty: ignore[invalid-argument-type] - _integer proved a whole number
    return found or ([_finding(location, message)] if message else [])


def _pitch(value: object, location: str) -> list[Finding]:
    """Check a wire pitch: a whole number of divisions above zero."""
    found = _integer(value, location)
    return found or ([_finding(location, "must be above zero")] if value < 1 else [])  # ty: ignore[unsupported-operator] - _integer proved a whole number


_GRID_KEYS = _table(
    {
        "module_mm": _module_mm,
        "divisions_per_module": _divisions,
        "wire_pitch": _pitch,
        "wire_pitch_fine": _pitch,
        "stretch_split": _enum("weight", "whole"),
    },
    required=("module_mm", "divisions_per_module"),
)


def _grid_table(value: object, location: str) -> list[Finding]:
    """Check the `[grid]` keys, then that the fine pitch divides the standard one."""
    found = _GRID_KEYS(value, location)
    if found or not isinstance(value, dict):
        return found
    message = pitch_error(
        value.get("wire_pitch", DEFAULT_WIRE_PITCH),
        value.get("wire_pitch_fine", DEFAULT_WIRE_PITCH_FINE),
    )
    return [_finding(location, message)] if message else []


def grid_from_data(data: Mapping[str, Any]) -> Grid:
    """Build the grid of a checked `[grid]` table or a bundle's `grid` object."""
    return Grid(
        data["module_mm"],
        int(data["divisions_per_module"]),
        int(data.get("wire_pitch", DEFAULT_WIRE_PITCH)),
        int(data.get("wire_pitch_fine", DEFAULT_WIRE_PITCH_FINE)),
        data.get("stretch_split", "weight"),
    )


def _lines_table(value: object, location: str) -> list[Finding]:
    """Check the `lines` table: a width above zero for a weight name, nothing else."""
    names = tuple(w.name.lower() for w in Weight)
    found = _map_of(_positive)(value, location)
    if isinstance(value, dict):
        found += [
            _finding(_child(location, key), f"unknown weight {_short(key)!r}: use one of {names}")
            for key in value
            if key not in names
        ]
    return found


def lines_from_data(data: Mapping[str, Any]) -> Mapping[Weight, float]:
    """Build the line widths of a checked `[lines]` table or a bundle's `lines` object."""
    return MappingProxyType({Weight[key.upper()]: width for key, width in data.items()})


_BUNDLE = _table(
    {
        "schema": _schema_version,
        "standard": _string,
        "symbols": _map_of(_bundle_symbol),
        "wires": _wires,
        "font": _FONT,
        "grid": _grid_table,
        "lines": _lines_table,
    },
    required=("schema", "standard", "symbols"),
)


def validate_bundle(data: object) -> tuple[Finding, ...]:
    """Check a decoded `bundle.json`: its three keys, and every symbol as a resolved symbol.

    Args:
        data: A decoded JSON document.

    Returns:
        One `schema` error per violation, located inside the bundle (`/symbols/S00227/ports/0`).
        A symbol is checked by `validate` and must also be resolved (no `parts`, `ports` an array,
        slots tables). Its key must be safe as a file name (`is_file_stem`: letters, digits, `_`
        and `-`, joined by single dots) and equal its `reference.number`, as a number equals
        its file stem. Empty when `library_from_bundle` may be called.
    """
    found = list(_BUNDLE(data, ""))
    if isinstance(data, dict) and isinstance(data.get("symbols"), dict):
        for key, symbol in data["symbols"].items():
            if not is_file_stem(key):
                found.append(
                    _finding(
                        _child("/symbols", key), f"{_short(key)!r} cannot be used as a file name"
                    )
                )
            reference = symbol.get("reference") if isinstance(symbol, dict) else None
            number = reference.get("number") if isinstance(reference, dict) else None
            if isinstance(number, str) and number != key:
                found.append(
                    _finding(
                        _child(_child(_child("/symbols", key), "reference"), "number"),
                        f"must equal the symbol's key {_short(key)!r}, got {_short(number)!r}",
                    )
                )
    return tuple(found)


def library_from_bundle(data: Mapping[str, Any]) -> Library:
    """Build a library from a validated bundle (D7).

    The bundle carries neither a title nor a number pattern, so the title is the standard and the
    pattern is empty.

    Args:
        data: A decoded `bundle.json` for which `validate_bundle` returned no findings.

    Returns:
        The library, its symbols keyed by the bundle's keys.
    """
    symbols = {number: symbol_from_data(s) for number, s in data["symbols"].items()}
    return Library(
        data["standard"],
        data["standard"],
        "",
        MappingProxyType(symbols),
        wires=_wires_from_data(data.get("wires", [])),
        font=font_from_data(data["font"]) if "font" in data else None,
        grid=grid_from_data(data["grid"]) if "grid" in data else DEFAULT_GRID,
        lines=lines_from_data(data.get("lines", {})),
    )


_VOCABULARY_LISTS = ("path_kinds", "potentials", "links")
_VOCABULARY = _table(dict.fromkeys(_VOCABULARY_LISTS, _array(_string)))
_RULES = _table({"required_slots": _array(_string)})


def _tables_problems(data: Mapping[str, Any]) -> list[Finding]:
    """Check the optional `[vocabulary]`, `[rules]`, `[[wire]]` `[font]`, `[grid]` and `[lines]`."""
    found: list[Finding] = []
    for key, check in (
        ("vocabulary", _VOCABULARY),
        ("rules", _RULES),
        ("wire", _wires),
        ("font", _font_table),
        ("grid", _grid_table),
        ("lines", _lines_table),
    ):
        if key in data:
            found += check(data[key], _child("", key))
    return found


def parse_config(text: str) -> tuple[LibraryConfig | None, tuple[Finding, ...]]:
    """Read `library.toml`: `standard`, `title` and `number_pattern`, all strings, the last a regex.

    An optional `package` names the data package's folder under `src/` (D45). The optional
    tables `[vocabulary]` (`path_kinds`, `potentials`, `links`) and `[rules]` (`required_slots`)
    hold lists of strings; an absent list is empty. The `[[wire]]` tables (`id`, `weight`,
    `style`) give the wire styles `wire` draws; an absent list is empty. The optional `[font]` table
    (`name`, `units_per_em`, `cap_height`, `ascent`, `descent`, `default_advance` and
    `[font.advances.normal]` and `[font.advances.thick]`, each one number per character, and
    `[font.heights]`, a capital height in millimetres by name) is the font text is measured with.
    Instead of the measured tables, `[font]` may hold `name`, `files = { regular, bold }`, two
    TTF paths relative to the folder of `library.toml` (D87), and `heights`; `files.py` measures
    the files and puts `heights` on the metrics (D93).
    The optional `[grid]` table (`module_mm`, `divisions_per_module`, a power of two, and the wire
    pitches `wire_pitch` and `wire_pitch_fine` in divisions) is the drawing grid; without it the
    grid is 2.5 mm, 8 divisions and pitches 8 and 4. The optional `[lines]` table gives the stroke
    width in millimetres, a number above zero, of each weight name (`normal`, `thick`). Once it is
    present, every weight a `[[wire]]` uses needs a width; an absent table is empty and checks
    nothing.

    Args:
        text: The file's TOML text.

    Returns:
        The config and no findings, or `None` and a `schema` finding per problem.
    """
    data, findings = parse_toml(text)
    if data is None:
        return None, findings
    problems: list[Finding] = []
    for key in ("standard", "title", "number_pattern"):
        if key not in data:
            problems.append(_finding("", f"missing required key {key!r}"))
        elif not isinstance(data[key], str):
            problems.append(_finding(_child("", key), "must be a string"))
    package = data.get("package", "")
    if not isinstance(package, str) or (package and not _PACKAGE.fullmatch(package)):
        problems.append(_finding("/package", "must be a Python package name: letters, digits, _"))
    problems += _tables_problems(data)
    if not problems:
        wires = _wires_from_data(data.get("wire", []))
        lines = lines_from_data(data.get("lines", {}))
        problems += [_finding("/lines", m) for m in lines_problems(wires, lines)]
    pattern = data.get("number_pattern")
    if isinstance(pattern, str):
        try:
            re.compile(pattern)
        except (re.error, OverflowError, RecursionError) as error:
            problems.append(
                _finding(
                    "/number_pattern", _short(f"must be a valid regular expression: {error}", 200)
                )
            )
    if problems:
        return None, tuple(problems)
    vocabulary = data.get("vocabulary", {})
    words = Vocabulary(*(tuple(vocabulary.get(k, ())) for k in _VOCABULARY_LISTS))
    required = tuple(data.get("rules", {}).get("required_slots", ()))
    return LibraryConfig(
        data["standard"],
        data["title"],
        data["number_pattern"],
        data.get("package", ""),
        words,
        required,
        _wires_from_data(data.get("wire", [])),
        font_from_data(data["font"]) if _literal_font(data) else None,
        grid_from_data(data["grid"]) if "grid" in data else DEFAULT_GRID,
        lines_from_data(data.get("lines", {})),
        *_font_files(data),
    ), ()
