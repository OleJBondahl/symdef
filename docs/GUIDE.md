# Guide to symdef

For someone writing a symbol set or consuming the toolkit. It assumes no standard: your set names its own
words and rules. The examples use one set of IEC 60617 symbols, because that is what the test fixtures hold.
New here? Start with the [tutorial](TUTORIAL.md). The binding spec is
[SYMBOL_INTERFACE.html](../src/symdef/docs/SYMBOL_INTERFACE.html) (the "spec" below):
this guide names the concepts and the calls, and the spec has the exact definitions. Where the
spec was silent, the choice is a numbered entry in [DECISIONS.md](DECISIONS.md) (D1, D2, ...).

## Concepts

- **Symbol.** A definition, not a placement: no tag, terminal number, position or orientation.
  Those belong to the drawing program that places it. `Symbol` is a frozen dataclass; `orient`,
  `translate` and `repeat` return new ones. Spec sections 2 and 4.
- **Port.** A place where a wire may attach, with an id, a position and a direction. Ids are
  roles (`in`, `out`, `anode`), never terminal markings such as `13` or `A1`. Spec sections 3
  and 4.
- **Node.** A set of ports that are one electrical point. A port in no declared node gets a node
  of its own (`nodes_of`, in `model.py`). Spec section 5.
- **Path.** A typed link between two ports (`from`, `to`, a `kind` word and `through`). The kind is a string
  from your set's `[vocabulary]`, such as `switch_open` in the IEC fixtures. Paths are the function as data,
  so a consumer can read connectivity without knowing any symbol. Spec section 5.
- **Slot.** A box the symbol reserves for text: the `tag` and one `marking.<port>` per port. The
  box grows from the slot point towards its `side`. Spec section 6; `slot_box` returns it.
- **Anchor.** A named point with a direction where another symbol can attach, used by composites.
  Spec sections 4 and 7.
- **Composite.** A symbol made of `parts`, each a reference to another symbol, attached by
  anchor. It copies no coordinates and inherits ports, slots and elements from its parts (D20).
  Spec section 7.
- **Repeat.** `repeat(symbol, n)` makes an n-pole symbol from a one-pole one, stepping by
  `pole_pitch`. The result is an ordinary symbol with ports such as `1.in` and `3.out` (D16).
  Spec section 7.

Units are modules (1 M = `DEFAULT_MODULE_MM`, 2.5 mm) on a drawing grid of `GRID_DIVISION` (0.125) M,
which `[grid]` in `library.toml` may change (see Measuring text and the grid); wires run on a 1 M grid. The wiring contract is linted in all 8 orientations (`Orientation`).

## Layout of a symbol set

```
library.toml          standard, title, number_pattern, package (optional), vocabulary, rules
symbols/<number>.toml one file per symbol; the file stem is the reference number
build/                generated: resolved JSON, SVGs, a gallery README
src/<package>/bundle.json   generated: every symbol, resolved
```

`symdef init DIR` writes a starter set, `symdef build DIR` writes the generated files, and
`symdef check DIR` runs every gate a set needs (D48). Exit code 0 is done, 1 is problems found.

`library.toml` of the test fixture (`tests/fixtures/guide/`):

```toml
#:schema https://olejbondahl.github.io/symdef/symbol.schema.json
standard = "IEC 60617"
title = "IEC 60617 symbols"
number_pattern = '^S\d{5}$'

[vocabulary]
path_kinds = ["conductor", "switch_open", "switch_closed", "impedance", "source", "diode"]
potentials = ["earth", "protective_earth", "functional_earth", "frame"]
links = ["mechanical_link"]

[rules]
required_slots = ["tag", "marking.<port>"]
```

`[vocabulary]` lists the words a symbol may use as a path kind, a node potential or a `via` link.
The toolkit has no built-in list. A word not listed fails the load with the word, the file and the
line (D46). `required_slots` lists the slot ids every symbol must carry; `marking.<port>` means one per port.
Both tables are strict: an unknown key is a finding. The `#:schema` line lets an editor check the file as you type.

`src/<package>` is the standard lowercased with only letters and digits (`IEC 60617` gives
`iec60617`). An optional `package = "name"` line in `library.toml` names the folder instead (D45).

A reference number must be a file stem: letters, digits, `_` and `-` in parts joined by single
dots (D31). A set holds data only; the toolkit and its gates come from this package.

## Defining a symbol

This is `symbols/S00227.toml` of the same fixture, a make contact:

```toml
schema = 1
name = "Make contact, general symbol"
kind = "symbol"
status = "unverified"
reference = { standard = "IEC 60617", number = "S00227" }

ports = [
  { id = "in",  at = [0, -2], dir = "N" },
  { id = "out", at = [0, 2],  dir = "S" },
]

paths = [
  { from = "in", to = "out", kind = "switch_open", through = true },
]

anchors = [
  { id = "link", at = [-0.5, 0], dir = "W" },
]

elements = [
  { line = [[0, -2], [0, -1]] },
  { line = [[0, 2], [0, 1]] },
  { line = [[0, 1], [-1, -1]] },
]

[slots]
tag           = { at = [-1.5, 0],    side = "W", box = [6, 1] }
"marking.in"  = { at = [0.25, -1.5], side = "E", box = [1.5, 1] }
"marking.out" = { at = [0.25, 1.5],  side = "E", box = [1.5, 1] }
```

A composite lists `parts` and maps its own ports to theirs (`S00254.toml`, the push-button,
attaches an actuator to the contact's `link` anchor):

```toml
parts = [
  { as = "contact",  use = "S00227" },
  { as = "actuator", use = "S00171", attach = "link", to = "contact.link", length = 2, via = "mechanical_link" },
]

ports = { in = "contact.in", out = "contact.out" }
```

`src/symdef/schema/symbol.schema.json` ships in the wheel and carries the `$id`
`https://olejbondahl.github.io/symdef/symbol.schema.json`. It describes the file structurally only
(D4, D47): any string is a valid path kind there, and the declared words are a load check. The rules that need
meaning are lint rules. A line may bind to a port with `port`, and the file's `schema` integer
did not step for it (D40).

## Loading and resolving

```python
from symdef import load_library

library = load_library(root)    # root is the set's directory
contact = library.get("S00227")  # UnknownSymbolError if absent
```

`load_library` reads `library.toml` and every `symbols/*.toml`, validates each file, resolves
composition and returns a `Library`. A `Library` has `standard`, `title`, `number_pattern`,
`symbols`, `vocabulary`, `required_slots` and `wires`; `len` and iteration work, and iteration is sorted by number. If any file has a
problem it raises `LibraryError` listing all of them, by file (D21). The pure core never raises:
problems are `Finding`s with the rule `schema` until `load_library` collects them (D3, D15).
Composite inheritance is D20; structural problems only the resolver sees are D17.

## Linting

`lint`, `RULES`, `finding_key`, `LibraryConfig`, `build`, `check`, `init`, `write_build` and `stale_build` are
the author door: import them from `symdef.authoring`. `symdef` itself holds what a consumer uses (D84).

```python
from symdef.authoring import lint
from symdef.lint import RULES

assert len(RULES) == 35
for finding in lint(contact, library.required_slots):
    print(finding.rule, finding.severity, finding.location, finding.orientation, finding.message)
```

There are 35 rules: the spec's 33 (section 9) and two of the toolkit's own, `lead-off-port`
(D40) and `stretch-cut`. `lint` takes a symbol in base orientation and your set's `required_slots`. That list is empty by default,
so no slot is required. It runs the orientation-dependent rules in all 8 itself (D6, D23, D46). It returns a tuple of `Finding`, each with `rule`, `severity` (`Severity`),
`message`, `location` (a string or `None`) and `orientation` (or `None`). They are ordered by the spec
table, then orientation, then location (D23, D34).

A symbol can exempt a rule with `lint_allow`, a list of `{ rule, reason }` (S00016, the
connection point, exempts three). `lint` removes the findings of the named rules, and reports
`allow-unknown` and `allow-unused` for exemptions that name no rule or never fire. The rules the
resolver reports cannot be exempted (C3). The spec's push-button example fails `pitch-overflow`
as written; see C1 in DECISIONS.md.

## Building

```python
from symdef.authoring import stale_build, write_build

write_build(library, root)
assert stale_build(library, root) == ()
```

`write_build` is what `symdef build` calls after loading and linting. It writes, under the set's `root`:

```
build/resolved/<number>.json   one resolved symbol (D11, D30)
build/svg/<number>.svg         plain
build/annotated/<number>.svg   ports, anchors, slots, lanes and sample texts (D33)
build/README.md                the gallery table
src/<package>/bundle.json      every symbol, resolved
```

`<package>` is the standard normalised to lowercase letters and digits (D8): `IEC 60617` gives
`iec60617`, and a standard with no letter or digit cannot be built (D35). Files are written as
bytes with LF endings and nothing is deleted. `stale_build` returns the files that are missing,
differ, or sit under `build/resolved`, `build/svg` or `build/annotated` without a symbol behind
them (D31). `symdef check` reports the same files as `stale-build`, so a committed build cannot go stale.
`scripts/build.py` in this repo is unrelated: it writes this package's `_version.py`.

## Serialized form

Resolved JSON has the symbol's fields with composition flattened and the `lint_allow` list kept
(D1, D11). The bundle is `{"schema": 1, "standard": ..., "symbols": {...}}` (D7). A library with wire styles adds `"wires": [...]` (D56).
`load_bundle(path)` reads a `bundle.json` back into a `Library` without the TOML sources; it
validates every symbol and requires the resolved form (D31). A package that ships a set
loads its bundle this way at import.

## Rendering

```python
from symdef import Orientation, orient, repeat, to_fragment, to_svg

breaker = orient(repeat(contact, 3), Orientation.R0)
svg = to_svg(breaker, annotate=True, texts={"tag": "-Q1"})
group = to_fragment(breaker)
```

`to_svg(symbol, *, module_mm=..., annotate=False, texts=None)` returns a standalone SVG document
whose viewBox is in module units. `annotate=True` adds the keep-out box, port labels, anchors,
slots and wire lanes; `texts` maps slot ids to sample text. `to_fragment(symbol)` returns a
placeable `<g>` fragment instead of a document (D39). Both are total: any input renders (D32).
`body_box`, `keepout_box` and `slot_box` give the boxes (`slots_box` the slots without the body), and `on_grid(v, tol, grid)` and `snap(v, grid)` the grid (the default grid when none is given).

`to_fragment_mm` (D52) returns the same fragment with every size in millimetres and no scale
transform. Coordinates and radii are multiplied by `module_mm`. Stroke widths come from
`weights_mm`, dash lengths from `dash_mm`, and the font size from `font_mm`, all in the caller's
millimetres. Use it when a drawing must show each size exactly as given. `to_svg` and
`to_fragment` keep their output.

## Stretching and tables

A symbol whose size is decided at placement time carries a cut line, `[[stretch]]` with `axis`
(`x` or `y`) and `at` (D53). `stretch(symbol, axis, length, offsets=None)` moves every point
beyond a cut: element points, ports, anchors and slot corners. A line or polyline across a cut gets
longer; a circle, arc or text across any cut raises `InvalidValueError`, and the lint rule `stretch-cut`
reports it first (D55). `offsets`
puts named ports, with their leads and `marking.<port>` slots, at coordinates along the axis. The
result is an ordinary symbol without that axis's stretch, so `orient` and `to_fragment` come
after it.

```python
from dataclasses import replace

from symdef import (
    Direction, Line, Orientation, Point, Polyline, Port, Reference, Slot, Status, Stretch,
    Symbol, SymbolKind, orient, stretch, to_fragment,
)

xs = {"1": 4, "2": 12, "3": 20, "4": 28}
card = Symbol(
    name="Card",
    kind=SymbolKind.SYMBOL,
    status=Status.UNVERIFIED,
    reference=Reference("IEC 60617", "C00001"),
    elements=(
        Polyline((Point(0, 0), Point(32, 0), Point(32, 8), Point(0, 8)), closed=True),
        *(Line(Point(x, 8), Point(x, 10), port=k) for k, x in xs.items()),
    ),
    ports=tuple(Port(k, Point(x, 10), Direction.S) for k, x in xs.items()),
    slots=(
        Slot("tag", Point(2, 2), Direction.E, (4, 1)),
        *(Slot(f"marking.{k}", Point(x, 12), Direction.S, (3, 1)) for k, x in xs.items()),
    ),
    stretch=(Stretch("x", 16),),
)
wide = stretch(card, "x", 112, {"1": 8, "2": 40, "3": 64, "4": 104})
drawn = orient(wide, Orientation.R0)
svg = to_fragment(drawn)  # pass texts= in the SVG calls to fill the slots
```

A frame is a symbol with a stretch on both axes and a label slot at a corner;
`stretch(stretch(frame, "x", 120), "y", 80)` makes it 120 by 80 (D53).

`table(row, n, axis, head=None)` makes `n` copies of a row, each stepped by the row's body extent
along the axis (D54). Copy `k` prefixes its ports `<k>.`, renames `marking.<port>` to
`marking.<k>.<port>` and any other slot `<id>` to `<k>.<id>`. A `head` keeps its own ids and, if it
has a stretch on the axis, is first stretched to the rows' total extent on that axis; without one it
keeps its width. The head stays where it is authored, relative to row 1. The cap is 64 rows.

```python
from symdef import body_box, table

row = replace(card, stretch=())
head = replace(
    card,
    ports=(),
    elements=(Polyline((Point(0, -4), Point(32, -4), Point(32, 0), Point(0, 0)), closed=True),),
    slots=(Slot("heading", Point(2, -2), Direction.E, (6, 1)),),
    stretch=(Stretch("x", 16),),
)
cores = table(row, 4, "x", head=head)
assert {"1.1", "4.4"} <= {p.id for p in cores.ports}
assert {"heading", "marking.2.1", "3.tag"} <= {s.id for s in cores.slots}
assert body_box(cores).width == 128  # the head spans the four rows
```

A symbol set declares wire styles in `library.toml` as `[[wire]]` with `id`, `weight` (`normal` or
`thick`) and `style` (`solid` or `dashed`). `wire(library, style_id, points)` returns an
element-kind symbol of one open polyline in that style; an unknown id raises `UnknownNameError`. The
resolved bundle carries the styles, so a library read with `load_bundle` can draw wires (D56).

```python
from symdef import Style, Weight, WireStyle, wire

styled = replace(library, wires=(WireStyle("link", Weight.NORMAL, Style.DASHED),))
link = wire(styled, "link", [(0, 0), (4, 0), (4, 6)])
assert link.elements[0].style is Style.DASHED
```

A closed polyline may say `fill = "tint"`. The caller passes the colour: `to_svg(symbol,
tint="#cfe8ff")`, `to_fragment(symbol, tint=...)` and `to_fragment_mm(..., tint=...)` take a
`#rgb`, `#rrggbb` or letters-only colour name, and without a tint a tinted polyline is unfilled
(D57).

```python
from symdef import Fill

shape = Polyline((Point(0, 0), Point(4, 0), Point(4, 4)), closed=True, fill=Fill.TINT)
tinted = replace(card, elements=(shape,))
assert 'fill="#cfe8ff"' in to_fragment(tinted, tint="#cfe8ff")
```

## Bound leads and muted symbols

A symbol's leads are the lines bound to a port with `port = "..."`. `leads(symbol, ports)` keeps
the leads of the ports you name and drops the rest, so an unwired port draws no stub. An id the
symbol does not hold raises `UnknownNameError`; after `table` or `repeat` the ids carry their prefix
(`1.a`). The toolkit knows no net: you decide which ports are wired (D59).

```python
from symdef import leads

wired = leads(card, ("1",))
assert [e.port for e in wired.elements if isinstance(e, Line) and e.port] == ["1"]
```

A line, polyline or arc may say `style = "dash_dot"`. `to_fragment` draws it with a dash of 1 M,
a gap of 0.25 M, a dot of 0.0625 M and a gap of 0.25 M; `to_fragment_mm` takes the four lengths
in millimetres as `dash_dot_mm` and raises `InvalidValueError` when a dash-dot element is drawn
without it (D60).

`to_fragment(symbol, muted="#888")` and `to_fragment_mm(..., muted="#888")` draw a symbol as not
installed: strokes, texts and fills in that colour, every line style as an even dash and gap of
the normal stroke width. Without `muted` the output is unchanged (D61).

```python
dim = to_fragment(card, muted="#888")
assert "#000" not in dim and 'stroke="#888"' in dim
```

## Weighted cuts, moving slots and ticks between rows

An axis may carry several cuts. Each has a `weight`, a number above zero that defaults to 1. The
growth, `length` minus the natural extent, is shared among the cuts in proportion to their
weights, and a point moves by the shares of the cuts it lies beyond (D67). With cuts of weight 1
and 3 grown by 8, the first takes 2 and the second 6: a point beyond both moves by 8, a point
between them by 2, and a line across the second grows by 6. A single cut takes the whole growth
whatever its weight. `offsets` applies afterwards, unchanged. Two cuts at the same `at` are a
`stretch-cut` finding.

A slot box is two corners, and `stretch` moves each like a point (D69). A box across a cut grows by
that cut's share, and a box wholly beyond one moves and keeps its size. So the room a slot has after
stretching is the stretched symbol's `slot_box`.

An element of a row symbol may say `between = true` (a line or polyline). `table(row, n, ...)`
draws it in rows 1 to n-1 and leaves it out of row n, so a row of four with one tick shows three
ticks and a single row shows none. A `between` element of the head is drawn as authored, and on a
symbol drawn on its own it is drawn as authored too (D70).

```toml
[[stretch]]
axis = "x"
at = 4
weight = 1

[[stretch]]
axis = "x"
at = 8
weight = 3

elements = [
  { line = [[0, 0], [12, 0]] },
  { line = [[2, -1], [2, 1]], between = true },
]
```

## Drawing slot text

`to_fragment(symbol, texts={...})` and `to_fragment_mm(..., texts={...})` draw the string you pass
for each slot, by slot id, after the symbol's elements. The slot's `side` sets the alignment
and a slot with `turn = true` reads bottom-up. A slot side is where text sits, and a port side is where a wire leaves. Keeping `C` out of `Direction` means a port can never be `C`. The side `C` centres the string on the slot point, and its box is centred on it too (D68). symdef never measures, shrinks or wraps a string:
`to_fragment_mm` draws at your `font_mm`, and `to_fragment` sizes to the box. An empty string draws
nothing; an id that is no slot raises `UnknownNameError`. `required_slots` (the entries `lint` takes)
makes a missing string an `InvalidValueError`, and the check runs only when `texts` is given (D63 to D65).

```python
from symdef import InvalidValueError

tagged = to_fragment(card, texts={"tag": "-A1", "marking.1": "1"})
assert tagged.count("<text") == 2
try:
    to_fragment(card, texts={"tag": "-A1"}, required_slots=("tag", "marking.<port>"))
except InvalidValueError as error:
    assert "marking.1" in str(error)
```

## Measuring text and the grid

A library may declare its font and its grid in `library.toml`; both are optional and frozen in the
loaded `Library` (`Library.font`, `Library.grid`).

```toml
[grid]
module_mm = 2.5            # above zero
divisions_per_module = 8   # a power of two
wire_pitch = 8             # divisions between wire lanes; every port sits on it
wire_pitch_fine = 4        # must divide wire_pitch; no third pitch

[font]
name = "Planted"           # a label, it changes no measure
units_per_em = 1000
cap_height = 700
ascent = 800
descent = 200
default_advance = 500      # for a character not listed below
[font.advances.normal]     # one advance table per weight, each its own glyph by glyph
A = 600
i = 300
[font.advances.thick]
A = 660
i = 340
[font.heights]             # optional: names to capital heights in mm
smallest = 1.8
body = 2.5
```

With no `[font]`, `Library.font` is `None` and a text measures 0.6 em per character and a capital
0.72 em tall, as before. `text_width(font, text, height, weight=Weight.NORMAL)` is the width of a
string; `body_box(symbol, font)`, `keepout_box(symbol, font)` and `slot_box(slot, text, height,
font)` measure with it. `slot_text(slot, text, height, font)` returns a `TextPlacement(point, anchor,
turned)`: where the string sits for the slot's side.

With no `[grid]` the grid is `DEFAULT_GRID` (2.5 mm, 8 divisions). `to_divisions(grid, v)` returns
the whole divisions of an on-grid value and raises `InvalidValueError` naming an off-grid one;
`from_divisions(grid, n)` is the reverse; `ceil_divisions(grid, v)` rounds a measured extent up to
whole divisions, ignoring float noise of 1e-9. `lint` takes the grid to check against. `snap(v, grid)`
and `on_grid(v, tol, grid)` take it as a trailing argument; with none they use `DEFAULT_GRID`, so a call
without a grid gives the output it always gave. `Grid(module_mm, divisions_per_module, wire_pitch=8, wire_pitch_fine=4)` raises
`InvalidValueError` for a module not above zero, divisions not a power of two, or a pitch that is not a whole number above zero or a fine pitch that does not divide the standard one, naming the value and the fix. A port off the standard pitch is a load error (`port-off-wiring-grid`). `FontMetrics.heights` holds the `[font.heights]` names; symdef does not interpret them.

## Measuring in whole divisions, and drawing where it was measured

`measure(symbol, orientation, library, texts=None, text_height=None)` returns a `Measure`: the body
box, keepout box, slot boxes and ports of the symbol turned to `orientation`, as `GridBox` and
`GridPort` values in whole divisions of `library.grid`. Boxes round outward; a port off the grid
raises `InvalidValueError`. `to_placed_fragment(symbol, orientation, at, library, ...)` draws the
turned symbol inside one `translate` read from a `GridPoint`, so the caller converts nothing.
`to_fragment_mm` is listed for removal in 0.13.

```python
from symdef import GridPoint, Orientation, measure, to_placed_fragment

contact = library.get("S00227")
measured = measure(contact, Orientation.R90, library)
assert measured.body.max.x > measured.body.min.x
fragment = to_placed_fragment(contact, Orientation.R90, GridPoint(16, 8), library)
assert "translate(" in fragment
```

Every error symdef raises derives from `SymdefError` (`InvalidValueError`, `UnknownNameError`,
`UnknownSymbolError`, `LibraryError`). None subclasses `ValueError`, `KeyError` or `OSError`, so catch
`SymdefError`. See [the changelog](CHANGELOG.md) for what moved in each release.

## Turning and small accessors

`orient_point`, `orient_direction` and `orient_box(box, orientation)` turn a point, a direction and
a box about the symbol's origin as `orient` does: mirror x first, then clockwise quarter turns.
`Box.union(*boxes)` joins boxes, `pole_pitch(symbol)` is the spacing `repeat` uses (the default
included), `pole_port(k, port_id)` is a port's id in pole `k`, and `nodes_of(symbol)` lists every
node, the declared ones then one per unlisted port.

`load_library` and `load_bundle` return a library whose `symbols` mapping is read-only: assigning
into it raises `TypeError`.

## Consuming

Install with `uv add symdef`, or pin the toolkit to an exact version from PyPI, never a range:

```toml
dependencies = ["symdef==X.Y.Z"]
```

Replace `X.Y.Z` with a released version. A change a consumer needs lands here first, is
released under a new tag, and the consumer then bumps its pin.
`LIBRARY_VERSION` is the installed version as a constant. The package has no runtime dependency
(D49). The spec ships as package data and is read through `importlib.resources` (D38).

## Where to read more

- The spec for exact definitions; DECISIONS.md for every choice the spec left open.
- `README.md` for the short tour, `CLAUDE.md` and `AGENTS.md` for how to work on the toolkit.
