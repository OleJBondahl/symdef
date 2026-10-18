# Decisions

Where `SYMBOL_INTERFACE.html` (the guide) is silent, decisions are recorded here, one entry each:
what was decided, why, and what it costs if wrong. Concerns about the guide itself are recorded as
`C<n>` entries; the guide is never edited.

## D1. `Symbol` carries a trailing `lint_allow` field

Decided: `Symbol(name, kind, status, reference, elements, ports, nodes, paths, anchors, slots,
pole_pitch, lint_allow)`. The guide's signature stops at `pole_pitch`.
Why: `lint(symbol)` must apply exemptions and report `allow-unknown` / `allow-unused`, and the
resolved JSON carries `lint_allow` ("same schema as the source"), so a loaded bundle needs it.
Cost if wrong: one extra trailing field with an empty default; consumers that construct `Symbol`
positionally up to `pole_pitch` are unaffected.

## D2. Purity split: file IO lives in `build.py`, pure helpers in extra modules

Decided: every module is pure except `build.py`, which holds all file IO, including `load_library`
and `load_bundle` (the guide lists only `write_build` and `stale_build` there, but says `build` is
the only impure module and both load functions read files). Everything they do besides reading is
pure: `load.py` parses text and decoded data, `serialize.py` renders canonical JSON, `gallery.py`
renders the gallery README. `lint/` is a package with one module per rule group.
Why: the purity gate and the guide's "only impure module" rule cannot both hold otherwise.
Cost if wrong: moving two functions and re-exporting them.

## D3. The pure core never raises; problems are `Finding`s

Decided: parsing, validation and resolution return findings (`schema`, `metadata`, `id-format`,
`part-*`, `export-unknown`) instead of raising. `LibraryError` (carrying the findings) is raised
only by `load_library` in `build.py`. `repeat` states its preconditions with `deal.pre`.
Why: CLAUDE.md requires every module-level function in a pure module to be `@deal.pure` and not
raise; findings are also how the guide says composition rules are reported.
Cost if wrong: a consumer wanting exceptions wraps the result.

## D4. The JSON Schema is structural only

Decided: `schema/symbol.schema.json` checks types, required keys, enums, array shapes and "exactly
one shape key". It does not check the id pattern, the grid, positive sizes or the number pattern.
Why: those are lint rules (`id-format`, `off-drawing-grid`, `degenerate`, `metadata`); enforcing
them in the schema would make those rules unreachable from a file. The schema carries no `$id`,
because the guide names no canonical host for it; a consumer refers to the file by path.
Cost if wrong: a stricter schema is a compatible tightening later; an `$id` is one added key.

## D5. A port on a filled circle or filled closed outline counts as "on geometry"

Decided: for `port-off-geometry`, "on a circle" includes any point of a filled circle's disk, and
"on a closed outline" includes any point of a filled polygon's area.
Why: the guide's connection point S00016 has its ports at the centre of a filled dot and is stated
to pass `port-off-geometry` without an exemption.
Cost if wrong: S00016 would need one more `lint_allow` entry.

## D6. `lint` takes a base-orientation symbol and evaluates 8 orientations itself

Decided: `lint(symbol)` expects a symbol in base orientation. Orientation-invariant rules run once
(`orientation = None`); orientation-dependent geometric rules (`port-on-body-edge`,
`port-lane-clear`, `slot-overlap-body`, `slot-overlap-slot`) run on `orient(symbol, o)` for all 8
`o` and report the orientation. Base-orientation-only rules (`through-axis`, `pitch-overflow`)
run once. A `lint_allow` entry exempts a rule in every orientation and counts as used if the rule
fired in at least one.
Why: the guide requires "all 8 orientations" and gates "lints clean in all 8 orientations" without
saying who loops.
Cost if wrong: a data repo loops `orient` itself; findings would then carry no new information.

## D7. Bundle keys are exactly the guide's; a loaded bundle has a bare `Library`

Decided: `bundle.json` is `{"schema": 1, "standard": ..., "symbols": {...}}` and nothing else.
`load_bundle` returns `Library(standard, title=standard, number_pattern="", symbols)`.
Why: the guide fixes the bundle format exactly; `title` and `number_pattern` come from
`library.toml`, which the bundle does not ship.
Cost if wrong: two extra keys in the bundle and one in `load_bundle`.

## D8. The bundle package name is the normalised standard

Decided: `src/<package>/bundle.json`, with `<package>` = the standard lowercased with every
non-alphanumeric character removed (`IEC 60617` -> `iec60617`, `ISA 5.1` -> `isa51`).
Why: `write_build(library, root)` gets no package name and `library.toml` has no key for it.
Cost if wrong: an optional `package` key in `library.toml`; a rename of the output directory.

## D9. Small API shape decisions

- `Slot.box` is a `(width, height)` tuple; `slot_box(slot)` returns the resolved `Box`.
- `Text` has no `anchor` field (guide: always middle-anchored, always upright) and carries `weight`
  so an element round-trips through the file format losslessly; it is not rendered with it.
- `to_svg` has no `margin` parameter (the guide's signature has none); the margin is a constant.
- The old `Anchor` text-anchor enum is removed; `Anchor` is the composition attachment point.
- `InvalidSymbolError` and `DuplicateSymbolError` are removed with the registry they served.
  `UnknownSymbolError` stays for `Library.get`.
- `Library` is a frozen dataclass that holds a mutable `Mapping`, so `hash(library)` raises
  `TypeError`. A library is never used as a key or in a set, so it stays as it is; the mapping a
  caller hands in stays theirs to change. Cost if wrong: `MappingProxyType` in `load_library` and
  `library_from_bundle`.

## D10. Fixture layout

Decided: `tests/fixtures/guide/` is a mini data repo (`library.toml`, `symbols/`) holding the five
guide examples verbatim plus `S00171` (the qualifier the push-button example uses; the guide names
it but does not define it, so its geometry is ours). A test compares each verbatim file with its
code block in the guide. `tests/fixtures/broken/<rule-id>/` holds one broken mini library per lint
rule (`symbols/S00001.toml` is the failing file); `tests/fixtures/broken/library.toml` is the
default library config.
Why: `metadata` needs a file stem that matches a number pattern, and composition rules need
sibling files, so one directory per rule is uniform.
Cost if wrong: renames.

## D11. Resolved JSON is explicit

Decided: resolved JSON writes every element key that has a default (`weight`, `style`, `closed`,
`fill`) and every port `description`, so a consumer in another language needs no defaults. Keys
whose default is "absent" (`potential`, `edition`, `form`, `pole_pitch`, `lint_allow` when empty)
are omitted.
Why: the guide says consumers "never implement composition" and should be about thirty lines.
Cost if wrong: byte-level diff of every generated file.

## D12. Composite `nodes`

Decided: a composite's own `nodes` entries may only restate an inherited node (same port set) to
add a `potential`; any other node declaration in a composite is a `node-invalid` finding.
Why: the guide defers merging parts' nodes (section 14) and is silent on composite `nodes`.
Cost if wrong: one more inheritance rule.

## C1. Guide example S00254 (push-button) fails `pitch-overflow` as written

Concern: `S00254` declares no `pole_pitch`, so its pitch is 4. Its flattened body extends from
x = -2.5 or further (the dashed link from the contact's `link` anchor at (-0.5, 0) runs 2 M west to
(-2.5, 0), and the actuator sits at that end), and the inherited marking slots reach x = 1.75. The
extent from section 8 point 6 is therefore at least 4.25 M, more than 4, so `pitch-overflow` fires.
Computed with the fixture `S00171` (its geometry is ours, D10; its push bar runs 0.75 M west of its
`link` anchor): the body box spans x from -3.25 to 0, the slot boxes other than `tag` reach
x = 1.75, and the extent is exactly 5.0 M against the pitch of 4 (`tests/test_guide_lint.py`
asserts this). With `pole_pitch = 8` the example lints clean.
The guide says the five examples "must load and lint clean" and that only the four atomic ones were
machine-checked. Implemented as written; the guide-verbatim fixture is expected to produce exactly
that one finding, and a variant with `pole_pitch = 8` is clean. Owner to decide: add `pole_pitch = 8`
to the example, or shorten the link.

## D13. Box and angle edge cases the guide leaves open

Decided: a symbol without elements has the body box `Box(Point(0, 0), Point(0, 0))`, so its keep-out
box still contains the origin; an element with no points (a polyline with none) has that same origin
box as `element_box` but adds nothing to `body_box`; `orient` normalises arc angles into [0, 360)
under every orientation, `R0` included, so `R0` is the identity only for symbols whose arcs are
already normalised.
Why: `body_box` must not raise on malformed symbols (the linter reports them), and section 3 says
angles are normalised to [0, 360) without exempting `R0`.
Cost if wrong: a slot-only symbol's keep-out box grows to the origin; a symbol with an arc at
-90 or 360 reads back as 270 or 0 after `orient(symbol, R0)`.

## D14. File-format gaps the schema had to close

Decided: the schema (and `validate`) require `height` on a text element; `fill` on a circle,
`closed` and `fill` on a polyline, `weight` and `style` are optional with the defaults the model
already has. A file must contain `elements`, `parts` or both. `ports` is never required. `slots` is
required when `kind = "symbol"`, as section 4's key table says (an empty `[slots]` table satisfies
it; a symbol whose `[slots]` lacks `tag` or a marking still reads and trips the `slot-missing` lint).
Reversal: the first version of this entry made `slots` never required, which deviated from the guide
without need; the schema now has `if kind = "symbol" then required slots`, and `validate` the same.
`schema`, `pole_pitch` and `repeat` accept integral floats (`8.0`), as JSON Schema's `integer` does.
`repeat >= 1` is not a schema rule; the resolver must report it. Unknown keys are errors on every
table; the only extra top-level keys are the resolved form's `body_box` and `keepout_box`.
Why: the guide shows `height` in every text example and gives it no default; the rest follows
section 4 and D4.
Cost if wrong: `height` optional (default 1) is a compatible loosening; the rest is unchanged.

## D15. Reading reports through `schema` findings with pointer locations

Decided: every reading problem is a `Finding(rule="schema", ERROR)`: TOML syntax errors, schema
violations, and `library.toml` problems (missing or non-string `standard`, `title`,
`number_pattern`; a pattern that does not compile). `location` is a JSON Pointer such as
`/ports/0/dir`, with `~` and `/` in keys escaped; a problem with the whole file has `location =
None`. `library.toml` may carry unknown keys; they are ignored.
Why: the guide names only the `schema` rule for "the file fails validation" and says nothing of the
config file; one rule keeps `LibraryError` messages uniform.
Cost if wrong: a separate `config` rule id and a check that ignores unknown keys becoming strict.

## D16. What `repeat` does where the guide is silent

Decided: the result lists every node explicitly, one per pole, with the ports prefixed and
`potential` kept; a port in no declared node becomes a one-port node (`nodes_of`), so a symbol
without `nodes` still yields explicit ones. A slot id starting `marking.` is renamed per pole
(`marking.in` -> `marking.2.in`, `marking.c.in` -> `marking.2.c.in`); `tag`, `value` and any other
slot id come from pole 1 only, unprefixed. The dashed link line is normal weight and is appended
after every pole's elements; `lint_allow` is carried over unchanged.
Why: the guide names `tag` and `value` and the `marking.` prefix, and says "nodes and paths repeat
per pole" without saying how implicit nodes are treated.
Cost if wrong: an unknown slot id that should repeat is lost on poles 2..n; resolved JSON of a
repeated symbol lists nodes that were implicit before.

## D17. Structural problems `validate` cannot see are `schema` findings from the resolver

Decided: `validate` does not know a composite from an atomic file, and `repeat` states preconditions
as contracts, so `resolve_library` reports these itself, all as rule `schema`: `repeat` below 1,
above 64 (D22), or on a part whose file has no through path (at `/parts/<i>/repeat`); `ports`
as an array of tables in a file with `parts` (`/ports`); `ports` as a rename table, or a slot
given as a string reference, in a file without `parts` (`/ports`, `/slots/<id>`); two parts with the same `as`
(`/parts/<i>/as`, the later one). A file with any of them has no symbol.
Why: the guide names one rule, `schema`, for "the file fails validation", and `repeat` must not be
called in violation of its contracts.
Cost if wrong: a separate rule id and a fixture for it; a second `validate` pass in the schema.

## D18. What `part-anchor` covers, and where it points

Decided: besides an unknown anchor and anchors that do not face each other (`dA == -dT` after
`orient`), `part-anchor` covers the malformed placements: `to` that is not `part.anchor`, names no
earlier part, or names an anchor the part lacks (`/parts/<i>/to`); an unknown `attach` anchor or
`attach` without `to` (`/parts/<i>/attach`); `via` without `length > 0` (`/parts/<i>/via`); a part
after the first with neither or both of `attach` and `at`, `at` together with `to`, `length` or
`via`, and `to`, `length` or `via` without `attach` (`/parts/<i>`). The first part with none of
these sits at the origin. A negative `length` is placed as written (the guide only bounds it with
`via`). A target that is an anchor of a part that itself failed to place adds no finding.
Why: the guide gives the rule one line; every one of these makes the placement undefined.
Cost if wrong: a finding moves to another rule or location.

## D19. Findings are keyed by file stem, never cascade, and sort deterministically

Decided: `Resolution.symbols` and `.findings` are keyed by file stem (the number, when the
`metadata` rule is clean); `findings` lists only stems that have some. A symbol with only `metadata`
or `id-format` findings still resolves. A file whose part file is unknown, in a cycle, or itself
failed has no symbol, and only the file at fault reports: its users get no finding of their own.
`part-cycle` is reported on every file of the cycle, at the part that leads on, so the result does
not depend on which file the walk reaches first. Order: stems sorted, then the finding order of
D34, generation order after that.
`metadata` uses `re.search` with the config's pattern, since the guide's pattern anchors itself; a
pattern that does not compile matches nothing.
Why: findings on a user of a broken file only repeat what the broken file already says.
Cost if wrong: users of broken files also list a finding; a stricter `fullmatch` for patterns
without anchors.

## D20. Composite inheritance where the guide is silent

Decided: a composite's own `nodes` entry that restates an inherited node (same port set, in the
composite's port ids) replaces it and carries its `potential`, or the inherited one if it has none;
any other own node is appended, so the linter's `node-invalid` reports it (D12). A part port
exported under two names yields two ports at the same place in one node; paths use the first name.
When several inherited paths are `through` and the composite redeclares none with `through = true`,
the result has no through path (the linter then warns `through-missing`). Inherited paths keep
part order; the composite's own paths follow, and an own path removes the inherited path between
the same two nodes. Elements are ordered part by part, a part's `via` link line before its own
elements, then the composite's own elements. The composite keeps its own `lint_allow`,
`pole_pitch`, `status` and `kind` and drops its parts' (`resolve._compose`): guide section 7's
inheritance list covers ports, nodes and paths, anchors, slots and elements and is silent on these
four. Section 7 also says the composite "must redeclare the one that stays" when several inherited
paths are `through`; that is enforced only as the `through-missing` warning, which is what the
guide's own rule table makes of it (a warning), not as an error.
Why: the guide states the rules of inheritance, not these corners.
Cost if wrong: an order change in resolved JSON; nothing else.

## D21. `load_library` reports what it read, by file

Decided: `load_library` reads `library.toml` and `symbols/*.toml` as UTF-8, files in stem order; a
file that cannot be read (missing, unreadable, not UTF-8, a directory named `x.toml`) and a
missing `symbols/` directory are `schema` findings located at the file or directory name. It
raises one `LibraryError` holding every finding: `library.toml` first, then per file, each message
prefixed `<file name>: ` because a finding has no file of its own. Rule severity comes from the
registry (`lint/registry.py`, `rule_finding`): the eight resolver rules were registered with the
resolver, the linter's other 25 rules were added later, and all 33 are in one table.
Why: a data repo gate needs to know which file a finding is about.
Cost if wrong: a `file` field on `Finding` instead of a message prefix.

## D22. Every number is bounded, `repeat` is capped, the walk has no recursion limit

Decided: every numeric value in a source or bundle file must be finite with an absolute value of at
most 1e6 module units (1e6 M is 2.5 km). Both validators enforce it and stay in agreement: the
hand-written `validate` tests `not (-1e6 <= x <= 1e6)`, so NaN and infinity fail; the JSON Schema
has `$defs/number` and `$defs/integer` (used by every number and integer key, `pole_pitch` and
`repeat` included) written as `not { anyOf: [exclusiveMinimum 1e6, exclusiveMaximum -1e6] }`,
because jsonschema's `maximum` lets NaN through and this form does not (JSON has no NaN; a TOML
file does). The `schema` constant and the enum-like values are unaffected. The resolver also
rejects a part `repeat` above 64, like `repeat` below 1: a `schema` finding at
`/parts/<i>/repeat`, part not resolved; a direct call of `repeat(symbol, n)` is unchanged. The walk
over part files uses an explicit stack, so a chain of composites of any depth resolves, with no
depth cap; a `part-cycle` message shows the first 8 files of a cycle and `...` when it is longer.
`_matches` in `lint/file.py` treats a pattern that raises `OverflowError` or `RecursionError` as
matching nothing, as it does one that is not a valid regex.
Why: with bounded input all later arithmetic (`orient`, boxes, the coming overlap tests, placement
sums) is total, so the pure core can keep its promise never to raise (D3); `validate` accepted
integers of up to 4300 digits, which overflowed `int + float` in placement and made `repeat` hang.
64 poles is far beyond any real switching device.
Cost if wrong: a larger bound is a one-constant change in `load.py` and the schema; a symbol beyond
2.5 km or a 65-pole device cannot be written until then.

## D23. How `lint` runs the rules, orders findings and treats exemptions

Decided: a rule is one function `(Symbol) -> tuple[Finding, ...]`, one `Rule(id, severity, group,
orientation_dependent)` row in `lint/registry.py` and one entry in `CHECKS` in `lint/__init__.py`.
`run_checks` calls an orientation-dependent rule on `orient(symbol, o)` for the 8 orientations and
stamps `o` on its findings; any other rule runs once, with no orientation. `RULE_IDS` and the sort
order derive from `GUIDE_ORDER`, the 33 ids in the guide table's order (a test reads the table out
of the guide and compares). Findings sort by rule order, then orientation (none first, then R0 to
MR270), then location with numbers as numbers (`anchors[2]` before `elements[0]`, `elements[2]`
before `elements[10]`), then generation order. `lint_allow` removes a rule's findings, of both
severities and in every orientation, and an entry counts as used when the rule fired in any of
them before the removal. `allow-unknown` (a rule id outside the 33, or a reason that is empty
or only whitespace; two findings if both) and `allow-unused` (a known rule that did not fire) are
added afterwards, so they cannot be exempted; an unknown rule is never also unused; a known rule
that does not apply to the symbol (`slot-missing` on an element) did not fire, so it is unused;
duplicate entries for one rule are each judged alone; an entry with an empty reason still exempts
and is reported once. A rule only the resolver reports (`schema`, `metadata`, `part-unknown`,
`part-cycle`, `part-anchor`, `part-port-unexported`, `export-unknown`; `RESOLVER_RULES` in
`lint/registry.py`) never fires in `lint` and the resolver does not read `lint_allow`, so an
exemption naming one changes nothing and is not reported as unused (C3). `id-format` is not in
that set: `lint` runs it on a symbol's own ids, so an `id-format` exemption is judged like any
other (one aimed at a part id is reported unused, since only the resolver reports those). The
package exports the function `lint`, which shadows the subpackage as an attribute of
`graphical_symbols`: write `from graphical_symbols.lint import ...`, never
`import graphical_symbols.lint as m`.
Why: the guide says who loops over orientations nowhere (D6) and leaves the exemption corners open.
Cost if wrong: a change in `ordered`, in `exempt` or in the two exemption functions; a rule row and
a `CHECKS` entry per rule instead of one registration if the two are ever merged.

## D24. What the geometry, id and anchor rules count

Decided: `off-drawing-grid` tests exactly (`value * 8` is integral) every line, polyline and
closed-outline point, circle and arc centre and radius (not arc angles), text position and height,
anchor position, slot point and slot box side; port positions are `port-off-wiring-grid`'s. The
exact test is deliberately not `units.on_grid`, which is public and tolerant (1e-9): a consumer that
pre-checks with `on_grid` can accept a value the rule then rejects. It
gives one finding per element, anchor or slot, naming every value off the grid, located at
`elements[i]`, `anchors[i]` or `slots.<id>`. `degenerate` also covers a circle or arc radius of
zero or less, an arc whose angles are equal modulo 360, and an element equal to an earlier one,
which is reported at the later copy (three copies give two findings); "equal" is the dataclass
equality of the whole element, so `weight` and `style` count (a reversed line or a dashed copy is
not a duplicate); an element can have more than one finding. Symbol-level `id-format` checks port
ids and anchor ids (`ports[i]`, `anchors[i]`; part ids stay the resolver's).
`point_on_geometry(point, elements, *, endpoints_only)` in `lint/geometry.py` is the one test of "on geometry", tolerance 1e-9: on a line or polyline
segment, on a circle or arc curve (an arc's ends included), on a closed polyline's outline, inside
a filled circle or filled closed polyline (D5); text is not geometry. `anchor-off-geometry` uses
it whole; `endpoints_only` keeps only the ends of a line and of an open polyline, for
`port-off-geometry`. A polyline of one point is a dot; a filled open polyline has no area.
Why: the guide names the quantities but not the granularity of a finding or the corners.
Cost if wrong: locations and message text change; `endpoints_only` moves if ports are meant to
count a polyline's interior vertices.

## C2. `id-format` and `repeat` disagree about port ids

Concern: section 3 says port ids match `^[a-z][a-z0-9_]*$` and the dot is reserved for namespacing,
section 7 says `repeat` makes the ports `1.in`, `2.in`, and section 12 says every symbol with a
through path lints clean as `repeat(symbol, 3)`. `1.in` does not match the pattern, so the three
cannot all hold as written. `repeat` also accepts its own result (it has a through path), and
prefixes `<k>.` again, so `repeat(repeat(S, 2), 2)` has the ports `1.1.in`, `1.2.in`, `2.1.in`,
`2.2.in`. Implemented: a port id is valid if it matches the pattern or is one or more pole numbers
(`[1-9][0-9]*`), each followed by a dot, and then such an id (`(?:[1-9][0-9]*\.)+` and the
pattern, matched in full); anchor ids and part ids get no such form. A source file with an
authored port `2.in` or `1.2.in` therefore passes `id-format`. Owner
to decide: keep this, or have `repeat` be exempt from the id rule some other way (a `lint` that knows
a symbol was repeated, which its signature cannot).

## D25. An arc with a non-finite angle counts as its centre in the boxes

Decided: `element_box` and `body_box` reduce an arc's start and end angle modulo 360 before they
compute its extent, and an arc whose start or end angle is NaN or infinite has no swept extent, so
its extent points are just its centre. Finite angles behave as before.
Why: `arc_point` calls `math.cos` on the angle, which raises for infinity; `body_box` is called by
the linter on hand-built symbols and must be total (D3, D22).
Cost if wrong: a garbage arc shrinks a box to a point instead of being an error; files cannot carry
such angles (D22), so only hand-built symbols are affected. `arc_point` used to raise for an
infinite angle; since D32 it returns the centre, and the rule above stays in the boxes.

## D26. How overlap is computed and what the wire lane is clipped to

Decided: `lint/overlap.py` tests a shape against an open rectangle (a slot box or a lane). A line and
each segment of a polyline are tested exactly, with `Fraction`s, so touching is decided without
rounding; a circle is tested by squared distances (outline: nearest point closer than the radius,
farthest point farther; filled: nearest point closer), which are exact on the grid; an arc is cut at
the angles where its circle crosses the four lines of the rectangle and at its ends, and the middle
of each piece must be more than 1e-9 inside every edge (only the arc uses the tolerance). A closed
polyline is its outline, and if filled also its area by the even-odd rule (an outline that misses
the rectangle leaves the rectangle wholly inside or wholly outside, so its centre decides); an open
polyline is only its segments, however it is filled; a polyline of one point is a dot. A circle or
arc whose radius is not positive draws nothing. A text element is `element_box` shrunk by 1e-9 on
every side, because the width factor 0.6 is not a binary fraction and an edge that only touches
must stay touching. A rectangle with no area is overlapped by nothing, and any non-finite number
makes a shape overlap nothing. The lane of a port is the rectangle from the port to the edge of a
frame: the keep-out box united with every port position, grown by 1 M on every side (per symbol).
Why: the guide defines overlap but not the arithmetic, and the lane is unbounded.
Cost if wrong: the frame margin is one constant; a 1e-9 tolerance on segments would be a change in
one function. Consequence to know: an element that overlaps a lane always also pushes the body box
past its port, so `port-on-body-edge` fires with `port-lane-clear`; a text element does the same, because its box
is part of the body box too. Only a slot box can break the lane on its own, which is why the lane
fixtures use slot boxes.

## D27. What the Ports rules count

Decided: `port-duplicate-id`, `port-off-wiring-grid`, `port-off-geometry`, `port-on-body-edge` and
`port-lane-clear` give one finding per port at `ports[i]` (the later port for a duplicate id); the
lane finding names the first three offending elements or slots and counts the rest.
`port-spacing` and `port-position-shared` give one finding per later port, naming the first earlier
port it is out of step with (same `dir`, gap not a multiple of 2 M; same position, different node).
The grid and spacing tests are exact (`% 1`, `% 2`), so NaN and infinity fail them.
`port-off-geometry` is `point_on_geometry` with `endpoints_only=True` (D24): a bend of an open
polyline is not an end. `port-on-body-edge` compares exactly and requires the other coordinate to
lie in the side's closed extent. Nodes come from `nodes_of`; a port id listed by two nodes belongs
to the first, and two ports with one id are one node. `port-on-body-edge` and `port-lane-clear` are
orientation dependent (text boxes and slot boxes do not turn); the other five are invariant, which
a property test checks for random grid-multiple symbols in all 8 orientations.
Why: the guide names the rules, not their granularity.
Cost if wrong: locations and message text change; a per-pair report for spacing and shared
positions would list more findings for three or more ports on one side.

## D28. What the Connectivity rules count

Decided: nodes come from `nodes_of` (D27); a port id listed by two nodes belongs to the first.
`node-invalid` gives one finding per offending name at `nodes[i]`: an unknown port, or a port that
an earlier node lists already; a port named twice inside one node counts as listed twice.
`path-invalid` gives one finding per path at `paths[i]`, the first of: an unknown port (both
named), two ports of one node (`from == to` included), a repeat of an earlier path between the same
unordered pair of nodes (the earlier one is named). A path that joins one node to itself is not an
"earlier path". `through-count` gives one finding per through path after the first, at the later
path. `through-axis` checks every through path on its own, whatever `through-count` says: `a` is
the `to` port's y, which must be positive and whole (`a > 0`, `a % 1 == 0`), `from` must be at
`(0, -a)` facing N and `to` at `(0, a)` facing S, all compared exactly (`-0.0` is `0`); a path that
names an unknown port has no through-axis finding (`path-invalid` reports it), and the first port
with an id is the one used. `through-missing` is one finding for the whole file (no location):
`kind = "symbol"`, at least two nodes in `nodes_of`, no potential on any node, no through path.
`port-isolated` gives one finding per port at `ports[i]`: the port is named by no path (valid or
not), no declared node lists it together with another existing port, and its (first) node has no
potential. The fixtures of the Ports and Composition rules gained a `potential` on their single node
or a conductor path so the new warnings do not fire on them; the `through-count` fixture tolerates
`path-invalid`, because two through paths that are both right on the axis join the same two nodes.
Why: the guide names the rules, not the granularity, the corners, or which of two overlapping
rules reports a malformed path.
Cost if wrong: locations and message text change; a per-symbol `through-count` finding instead of
one per extra path.

## D29. What the Slots rules count

Decided: `slot-missing` (kind symbol only) gives one finding per missing slot, at that slot
(`slots.tag`, `slots.marking.<port id>`); ports that share an id need one marking slot, and
`value` is never required. `slot-unknown-port` (every kind) takes a slot whose id starts `marking.`
and looks up the rest of the id (only the first prefix is removed, so `marking.1.in` names the
port `1.in`); an empty rest is unknown. `slot-overlap-body` gives one finding per slot at
`slots.<id>` naming the first three overlapped elements, using `overlaps_rect` (D26).
`slot-overlap-slot` gives one finding per overlapping pair, at the later slot, naming both; boxes
without area overlap nothing. `pitch-overflow` (kind symbol only, base orientation, run once) has
two parts. A `pole_pitch` that is not a positive multiple of 4 is a finding at `pole_pitch`. For a
symbol with at least one through path the extent is `max.x - min.x` of `body_box` united with every
slot box whose id is neither `tag` nor `value`, and it must be at most the limit: `pole_pitch` if it
is positive (even when it is not a multiple of 4, so a pitch of 6 with an extent of 7 gives both
findings), otherwise 4. A symbol without a through path has no extent to check, as the guide
says "for a symbol with a through path". A through-path symbol with no elements has the origin
box (D13) as its body box. The two orientation-only fixtures rely on the box being upright: two
boxes 3 M wide and 1 M tall that stand 2 M apart vertically miss each other and overlap by 1 M once
the 2 M step is horizontal; a 1.5 x 3 M box beside a lead lies across it after a quarter turn.
Why: the guide names the rules, not their granularity or the corners.
Cost if wrong: locations and message text change; the limit for a `pole_pitch` that is positive
but not a multiple of 4 would be 4 instead.

## D30. What resolved JSON writes where D11 and the guide are silent

Decided: `ports`, `nodes`, `paths`, `anchors`, `elements` and `slots` are always written, as `[]` or
`{}` when empty (`slots` because the schema requires it for `kind = "symbol"`; the rest so a
consumer never tests for absence). `nodes` follows `nodes_of`: declared nodes in source order, then
one node per port in none. A path always writes `through`. Slots are a table written in slot-id order,
so a JSON object read back gives the slots in that order; a symbol's slot order is not preserved by
the round trip, and neither is a node list that was implicit. Text is canonical as `json.dumps` writes it
with `indent=2`, `sort_keys=True` and `ensure_ascii=False`, after every whole float has become an
int (`-0.0` prints as `0`), so a point is four lines; control characters in strings are escaped, so
no carriage return can occur. Floats print in Python `repr` form (`0.1`, `1e-05`), which is
valid JSON; grid values (multiples of 0.125) never take an exponent form. NaN and infinity have no JSON form: `to_json` writes `NaN`,
`Infinity` and `-Infinity` as Python's `json` does and does not raise; both validators reject them
(D22), so only a hand-built symbol can carry one.
Why: the guide fixes the text rules and the two computed keys and nothing else; `json.dumps` with
those options is what every language's standard pretty-printer produces plus a key sort.
Cost if wrong: a byte-level diff of every generated file; compact point arrays would need a
hand-written writer.

## D31. What the build writes, what stale means, what a bundle may contain

Decided: `serialize.py` holds `build_files(library) -> dict[str, bytes]` (path relative to the
repo root with `/`, in path order), `package_name` (D8) and `GENERATED_DIRS`; `gallery.py` holds
`readme`. `write_build` and `stale_build` in `build.py` both call `build_files`, so they cannot
disagree; both return `root / <relative path>` (relative if `root` is), ordered by their
relative `/` path; an unreadable file or unwritable path raises `OSError`. `write_build` creates directories, writes bytes (never text mode, so no `\r` on Windows)
and deletes nothing. `stale_build` reports a missing file, a directory where a file belongs, a
file with other bytes, and any file, at any depth, under `build/resolved`, `build/svg` or
`build/annotated` that the library does not produce; it looks at nothing else. Text UTF-8 cannot
encode (a lone surrogate, which JSON can carry) is written as `?`. The README has the standard, a
one-line note on status and a table (number linking to the resolved JSON, name, kind, status,
plain and annotated image); it uses `standard` and never `title`, so a library loaded from a
bundle builds the same bytes as the one loaded from the sources. A bundle is read by `parse_json`
and `validate_bundle` (both in `load.py`, pure) and `library_from_bundle`; `validate_bundle` checks
every symbol with `validate` and requires the resolved form (no `parts`, `ports` an array, slots
tables) and a key that is a file stem and equals the symbol's `reference.number`. A file stem is
letters, digits, `_` and `-` in parts joined by single dots (`5.1`, `ISO-14617-1.1`): the guide
says the number is the file stem and later standards (ISA 5.1, ISO 14617) have dots in theirs, so
dots must load; a leading, trailing or doubled dot, a separator, a space or an empty name cannot
name a file safely. `write_build` and `stale_build` raise `ValueError` for a library with a
number that is not a file stem, before reading or writing anything (`is_file_stem` in `load.py`
is the one test).
Why: the guide names the two functions and the layout; the rest keeps output byte-exact and keeps
a bundle from a stranger from writing outside the repo.
Cost if wrong: a number with another character (a space, `+`) cannot be a bundle key (relax
`_STEM` in `load.py`); extras outside the three directories stay unreported (add a directory to
`GENERATED_DIRS`); a data repo that wants stale extras removed writes that loop itself.

## D32. `to_svg` and `arc_point` are total; what the SVG does with input XML cannot carry

Decided: `arc_point` returns the arc's centre for a NaN or infinite angle (it used to raise from
`math.cos`), so `to_svg` never raises for a hand-built symbol. The boxes keep their own rule
(D25): an arc with a non-finite angle counts as its centre there even when its other angle is
finite, which `arc_point` alone would not give, so `_extent_points` still checks it. The number
formatter writes NaN and infinity as `0`; finite numbers are unchanged (at most 4 decimals, no
`-0`), so a huge value such as 1e300 is written out in full. Text in `<title>` and in every `<text>`
goes through one function: a character XML 1.0 cannot carry (C0 controls except tab, line feed and
carriage return, lone surrogates, U+FFFE, U+FFFF) becomes U+FFFD, not dropped, so the text keeps
its length; `&`, `<` and `>` become entities; a carriage return becomes `&#13;` (a parser reads
`\r` back, no `\r` byte reaches the file and `stale_build` stays stable on every platform). A line
feed and a tab stay as they are, because XML keeps both in character data. The annotation grid is
left out when the view is not finite or would hold more than 10 000 dots (100 by 100 M, 250 mm
square at the default module), because a dot per module of a 1e300 symbol would never finish.
Why: CLAUDE.md wants every module-level function pure and non-raising; a symbol name can carry
`"\r"` or a NUL from TOML, and a build the sibling repo compares byte for byte must be well-formed
XML with LF-only bytes.
"Never raises" covers the typed inputs, floats: a Python int beyond float range (10**400) in a
hand-built `Point` is outside the contract (the fields are `float`) and unreachable from files
(numbers are bounded to 1e6, D22).
Cost if wrong: a garbage symbol draws garbage numbers instead of an error; a real symbol above
100 by 100 M gets no grid in its annotated SVG (one constant); a `\r` in a name shows as `&#13;`
in the file.

## D33. What the annotated SVG draws, and the sample texts of the gallery

Decided: the guide says `annotate=True` draws "the grid, ports with ids and lanes, anchors, slot
boxes, and both boxes" and `texts` maps slot ids to sample strings. Drawn in this order, all inside
`<g class="annotation">`: the grid (`grid`, a dot at every whole module, D32); `body-box` (green)
and `keepout-box` (purple), both dashed 0.2/0.2, the keep-out one offset by 0.2 so they alternate
where they coincide; per slot, in slot-id order, a translucent `slot-box` (blue) and its id (`slot-id`,
size 0.3) just above the box; per anchor a teal diamond of half-size 0.2 (`anchor`) and its id
(`anchor-id`, size 0.4) centred 0.75 M out along the anchor direction; the `lane` of every port, a
red translucent strip 0.5 M wide from the port along its direction to the edge of the view; then
per port a red dot (`port`) and its id (`port-id`, size 0.6, centred 1 M out). The elements are
drawn first, under all of it. The view is the keep-out box united with every port label box, every
lane start (0.5 M across), every anchor marker and label and every slot label, plus 1 M on every
side; a port or anchor label box is 1 em wide per character (0.6 M per character at size 0.6, 0.4 M
at 0.4; the code keeps the half-width, 0.3 and 0.2 M per character), a little wider than the
glyphs, a slot label box is 0.6 em per character (0.18 M at size 0.3, the guide's own text width),
and each is one font size high. Plain, the view is the body box, plus the slot boxes of the texts
that are drawn. Sample text (`<g class="samples">`, drawn last, in both modes, class
`sample-text`, orange, no stroke, upright, `font-family="sans-serif"`): the font size is the
largest `s <= 1` with `s <= h` and `0.6 * s * characters <= w`, rounded down to 4 decimals; a
slot with no text, an empty one, a box without a positive size, or an id the symbol has no slot
for gets nothing. Vertical placement uses explicit baselines and no `dominant-baseline`, which
several renderers (MuPDF, cairosvg) ignore: E and W put the baseline 0.36 s below the slot point (a
capital is about 0.72 s tall, so it is centred on the point), N puts it on the point, S 0.72 s
below (the capitals hang from the point). The port id labels use the same 0.36 rule instead of
`dominant-baseline="central"`, so they moved 0.216 M down, and so does a symbol's own `Text`
element (its baseline is `at.y + 0.36 * height`, so the capitals are centred in the text box the
guide defines; it was `at.y`, which put them above the box). Slots are drawn in id order because
resolved JSON keeps them in id order (D30): a symbol loaded from a bundle must give the same
bytes as the one from the sources. The build (`build_files`) draws `build/annotated/<n>.svg` with
`sample_texts(symbol)` from `gallery.py`: `tag` is `-X1`, `value` is `10 A`, `marking.<port id>` is
the 1-based position of the port in `symbol.ports` (the first, for ports that share an id); the
plain `build/svg/<n>.svg` stays the bare definition.
Why: the guide names what is drawn, not how; the gallery must show a filled-in symbol, and a
sample text that does not depend on the symbol name keeps the files small and stable.
Cost if wrong: every annotated SVG changes (colours, sizes, label places are constants); a
different sample changes every annotated file; the 0.6 M per character width is the guide's own
text extent, and a real font is a little wider for some strings (`marking.out` at size 0.3 fits
its label box only about).

## D34. One finding order for the resolver and the linter

Decided: `finding_key` in `lint/registry.py` is the one sort key for a `Finding`, used by
`resolve_library` (per file) and by `lint.ordered`. It sorts by the rule's place in the guide's
section 9 table (`GUIDE_INDEX`; a rule outside the table after all of them, by id), then by
orientation (none first, then R0 to MR270), then by location with numbers compared as numbers
(`/parts/2` before `/parts/10`, `elements[2]` before `elements[10]`), then by generation order.
A data repo that concatenates `LibraryError.findings` and `lint` results and sorts them with
`finding_key` gets the table's order across both. The resolver used to sort by rule id in
alphabetical order (`id-format` before `metadata`, `export-unknown` before `part-port-unexported`).
Why: two orders for the same rules had no single rationale, and the table is the guide's own.
Cost if wrong: a change in one function; resolver findings of different rules swap places.

## C3. `lint_allow` cannot exempt the rules the resolver reports

Concern: guide section 4 calls `lint_allow` "the only way to be exempt from a lint rule", section 9
says composition and file rules "are reported the same way", and section 8 says an exemption whose
rule would not have fired is itself an error. The resolver's rules (`schema`, `metadata`,
`part-unknown`, `part-cycle`, `part-anchor`, `part-port-unexported`, `export-unknown`, and
`id-format` of a part id) run in `resolve_library`, outside `lint`, which never reads `lint_allow`;
the three statements cannot all hold for them.
Implemented as: these rules are not exemptable. An entry that names one of the seven that only the
resolver reports changes nothing, and `allow-unused` does not fire for it, so a mistaken entry is
inert and does not add a second error next to the original one (`id-format` is still judged by
`lint`, see D23). Cost if wrong: applying `lint_allow` in `resolve_library` to the composite's own
findings, and reporting an entry there as unused when the rule did not fire; the two exemption
functions in `lint/exemptions.py` would then serve both places. Owner to decide whether these rules
are formally non-exemptable or the resolver should apply `lint_allow`.

## D35. A standard with no letter or digit cannot be built

Decided: `write_build` and `stale_build` raise `ValueError` when `package_name(library.standard)`
is empty (a standard such as `...` or `-`), before reading or writing anything, the same error
type as for a number that is not a file stem (D31). `load_library` and `validate` still accept such
a standard: the check is in the impure shell (`_check_names` in `build.py`), not in `validate`,
`parse_config` and the bundle validator, which would each need a rule for it.
Why: D8 makes the package the standard with everything but letters and digits removed, so an empty
package would write `src/bundle.json` instead of `src/<package>/bundle.json`, silently.
Cost if wrong: a `schema` finding on `standard` in `parse_config` and `validate_bundle`, so
`load_library` reports it, and a matching key in the JSON Schema.

## D36. `deal` is the one runtime dependency, kept for the purity contracts

Decided: every module-level function in a pure module carries `@deal.pure`, checked at import
time, and `deal` is a runtime dependency of the package, not a dev dependency. No other
third-party package is added to `src/`; `jsonschema` stays a dev-only dependency of the schema
agreement test. This carries forward the reasoning of the Schematika v2 monorepo's decision 0008
from the interval this package spent as `packages/graphical-symbols` in that workspace, where a
boundary test enforced `deal` as the package's only allowed third-party import; that test does not
exist here, so this entry is the record now that the package is its own repository again.
Why: `scripts/fp_purity_gate.py` fails the build when a pure-module function is missing the
decorator, and the decorator is a runtime contract, so it cannot be moved to a dev group.
Cost if wrong: a second third-party import in `src/` with no record here, or `deal` dropped
without a replacement for the purity contracts it checks.

## D37. Build-time file access is confined to `build.py`, `load_bundle` and `load_library`

Decided: `load_library`, `load_bundle`, `write_build` and `stale_build`, and `scripts/build.py`,
read and write symbol source and build files as a build-time tool whose output is tracked data
(`build/`, `src/graphical_symbols/bundle.json`-shaped output for a consumer, the gallery). No
other module reads or writes a file; the pure core takes values and returns values.
`scripts/fp_purity_gate.py` exempts `build.py` by name, the same way `tests/test_boundaries.py`
in the Schematika v2 monorepo exempted it while this package lived there as
`packages/graphical-symbols` (that workspace's decision 0009, which also recorded
`electrical_symbols` reading its packaged `bundle.json` at import -- a fact about that package,
not this one, and no longer this repository's concern).
Why: symbol data is compiled by a developer running the build, not read at render time; the
toolkit itself never touches a file outside that build step.
Cost if wrong: a file read or write anywhere else in `src/` needs a new decision record and a
`fp_purity_gate.py` exemption, which the gate's own can-fail test would then have to prove.

## D38. The design guide is package data, read through `importlib.resources`

Decided: `docs/SYMBOL_INTERFACE.html` moved (`git mv`, history kept) to
`src/graphical_symbols/docs/SYMBOL_INTERFACE.html`. Hatch's wheel config already packages
everything under `src/graphical_symbols/`, so the file needs no new build-system entry: it sits
at the same relative path in the source tree and in the built wheel. A consumer reads it with
`importlib.resources.files("graphical_symbols").joinpath("docs/SYMBOL_INTERFACE.html")`, which
resolves the same way whether the package is installed from an editable source checkout, a git
dependency, or a built wheel. `tests/test_guide_package_data.py` proves the resource resolves and
carries the guide's own `<title>` (not a byte count, which would break on every edit to the
guide's prose and tests the wrong property).
Why: `electrical-symbols` compares its data byte for byte against this guide's worked examples
(its own D38, the "verbatim gate"), and until this toolkit left the Schematika v2 monorepo the two
packages shared one copy through a sibling directory. Now they are two repositories; the toolkit's
wheel never shipped `docs/`, so the sibling path stopped resolving. Moving the guide under the
package directory keeps exactly one copy, and it is the toolkit's own, which is the only copy a
downstream gate can check against and still mean anything (a vendored copy in the downstream
package would only prove agreement with itself).
Cost if wrong: a consumer with a stale copy or a broken resource path silently stops checking
against the real guide; `test_guide_package_data.py`'s can-fail test is the guard against a
resource that resolves but is not this file's content.

## D39. `to_fragment`: a placeable `<g>` fragment beside the standalone document `to_svg`

Decided: `svg.py` gains `to_fragment(symbol: Symbol) -> str`, returning `_GROUP_OPEN`, one
`_element(e)` per `symbol.elements` and `</g>`, joined by newlines with a trailing one -- exactly
the plain content group `to_svg` already builds, reusing `_element` and `_GROUP_OPEN` directly
rather than a second element-rendering path. No `<svg>` root, no `<title>`, no annotations, and no
sample texts: the function takes no `texts` parameter at all, so a slot's sample text can never
reach a fragment, not merely because no fixture happens to exercise it. It applies no transform,
scale or orientation of its own; the caller places it in its own coordinate system. Exported from
`graphical_symbols.__init__` alongside `to_svg`.
Why: `schematika_render` (the Schematika v2 monorepo's render package) assembles a page out of
several placed symbols and needs each one as a reusable piece it positions and scales itself, not
a whole standalone document; the guide (`SYMBOL_INTERFACE.html`) defines only the standalone
`to_svg` document and is silent on an embeddable fragment.
Cost if wrong: reusing `_element`/`_GROUP_OPEN` means any future change to how an element renders
is automatically picked up here too; if a future edit ever duplicated that logic instead, the
fragment and the document's plain mode could silently drift apart. A wrong function name is a
rename in two files (`svg.py`, `__init__.py`) and the tests that check it.

## D40. A line binds to a port with `port`; the file's `schema` integer does not step

Decided: `Line` gains a trailing field `port: str | None = None`, written by `line = { ...,
port = "in" }`. It is optional, additive and carries no default that changes an existing file's
meaning, so `schema` (the file-format marker, `const 1` in the JSON Schema and
`_schema_version`) stays 1: nothing that validated before stops validating, and nothing that
validates now would have validated under the old rule differently. A new lint rule
`lead-off-port` (ERROR, Ports group, guide section 9) fires when the named port does not exist,
or when it does but neither end of the line is at the port's position, or the line does not run
along the port's facing axis (the coordinate perpendicular to the port's direction must be equal
at both ends) -- one finding per offending line, at `elements[i]`. The resolved JSON writes
`port` only when set (D11's "absent" pattern, like `edition` and `pole_pitch`). `orient` and
`translate` carry `port` along for free through `dataclasses.replace`. `repeat` prefixes a bound
lead's `port` with `<k>.`, the same prefix it gives the port itself, so a repeated symbol's leads
stay bound. Composition namespaces a part's bound lead `<part>.<child port>` while placing it,
then rewrites that to the rename map's exported id once `_export_ports` has computed it; a lead
bound to a part port the rename map leaves out keeps the namespaced, unreachable id, which is
moot because `_export_ports` already fails the file on `part-port-unexported` for that port. A
part port the rename map exports under more than one new id (`{ a = "c.in", b = "c.in" }`) gives
a bound lead the first one the map declares: both exported ports still share the child's position
and direction, so the choice only decides which one the lead's own metadata names, never where
either one draws or routes; `test_resolve.py`'s
`test_a_lead_on_a_port_exported_twice_follows_the_first_declared_alias` pins it.
Why: the package version (`pyproject.toml`, currently 0.1.2) is this repo's only versioning
mechanism with a minor/major/patch structure; the work order that asked for this expects the
release that carries it to be tagged a minor step (`v0.2.0`) on that scheme, not on `schema`,
which is a single flat integer with no such structure and no precedent of ever moving off 1. A
consumer on the old tag simply never emits `port`; a consumer that needs it takes the new tag,
same as any other public addition here (CLAUDE.md's "coordinated change"). The `port-lane-clear`
guarantee already makes a wire reaching a port along its own axis safe at `t = 0`; `lead-off-port`
only makes sure a claimed binding actually is that wire, so a downstream renderer (or anything
else) can trust `element.port` without re-deriving it from geometry.
Cost if wrong: an unmapped `repeat` or composition would leave `element.port` naming a port that
no longer exists after flattening, silently turning every downstream reader's binding lookup
into "unbound" instead of a loud finding; `test_repeat.py` and `test_resolve.py` each gained one
test against exactly that. If the owner ever wants `schema` itself to carry a minor/major split,
that is a bigger, separate decision: nothing here depends on it.

## D41. Public, plain-markdown docs; v0.3.0; exact git tag; no PyPI for now

Decided (owner 2026-10-01): the repo's documentation is plain markdown in the repo, with no
documentation site: `README.md` (install, one worked example, the concepts), `docs/GUIDE.md`
(the concepts in more depth: how symbols are defined, built, linted and serialized) and
`AGENTS.md` (a pointer for any agent: `CLAUDE.md` holds the rules; the README and
`docs/GUIDE.md` serve users). Every public name in `__all__` carries a short Google-style
docstring. The Python examples of the README and `docs/GUIDE.md` are run by
`tests/test_readme.py`, so they cannot drift. The docs may name the toolkit's users; the rule
that nothing names a Schematika package covers code, tests and scripts (designer 2026-10-01).
The release that carries this is `v0.3.0`; consumers install by exact git tag (`uv add
"graphical-symbols @ git+https://github.com/OleJBondahl/graphical-symbols@v0.3.0"`). The package
is not published to PyPI for now.
Why: the toolkit is consumed by an exact tag already (D38's package data, Schematika's pin), a
site or an index would add upkeep with no reader today, and the tests keep the examples true.
`CLAUDE.md` stays the one home of the agent rules: a draft `AGENTS.md` that restated them
disagreed with `CLAUDE.md` about `docs/` on the day it was written.
Cost if wrong: if a consumer outside the tag workflow appears, PyPI publication is a later,
separate decision (trusted publishing and a release workflow); nothing here blocks it. The docs
are only as true as their tests: their prose is not run.

## Open questions for the owner

- C1 (S00254 fails `pitch-overflow` as written): add `pole_pitch = 8` to the guide's example or
  shorten the link. The real `iec60617` `S00171` may change the extent; report the outcome there.
- C2 (`id-format` versus `repeat`'s `<k>.` port ids): keep the prefix form permanently, or change
  the guide's id pattern.
- C3 (`lint_allow` and the seven resolver-only rules): formally non-exemptable, or apply
  `lint_allow` in `resolve_library`.
- Merging `feat/toolkit` into `main` is the owner's call; nothing has been merged.

## Known limits, decided not to bound

Each is reachable only from the data repo owner's own files, and the guide is silent. Cost if
wrong: add a bound and a `schema` finding, as D22 did for numbers and `repeat`.

- `resolve_library`: nested composites with two parts each fan out as 2^depth elements (depth 16 is
  about 2 s; about 40 tiny files would not finish).
- A catastrophic-backtracking `number_pattern` in `library.toml` (for example `(a+)+$`; the time
  grows by 4 per 2 characters) can hang `re.search`. It is the only non-terminating path in the
  core. `^S\d{5}$`-style patterns are safe.
- Lint cost is quadratic in the number of poles of a `repeat`ed device (64 poles about 21 s, 24
  poles 2.8 s; `deal` tracing is about 2.2 times of that). The gates need only `repeat(s, 3)`.
- `load_library` accepts a file stem or `number_pattern` that yields a number failing the stem
  regex (`a b.toml`, or a Windows device name such as `CON`); `write_build` and `stale_build` then
  raise `ValueError` (D31), and `build/svg/CON.svg` would misbehave on Windows.
- `validate` still raises on a mapping key that is a 4300-digit integer (unreachable from TOML or
  JSON); some private module-level tables (`orient._PARTS`, `load._ELEMENTS`, `svg._SAMPLE_ALIGN`,
  `geometry._RIGHT_ANGLE_COS_SIN`) are mutable dicts.
- In the annotated S00227 the sample text `-X1` covers the start of the `link` anchor label,
  because the guide's `tag` slot ends 1 M west of that anchor. Cosmetic, gallery only.

## What `../iec60617` must do because of these decisions

- Add `.gitattributes` with `* text=auto eol=lf`; without it, on Windows with `core.autocrlf=true`,
  tracked build files become CRLF and `stale_build` reports everything stale.
- Run `write_build` again: the `Text` baseline fix (D33) changed the bytes of every SVG that contains
  a `Text` element, so any committed build is stale.
- Use `finding_key` (`graphical_symbols.lint.registry`, D34) to sort the concatenated
  `LibraryError.findings` and `lint` results; wrap `load_bundle` at import time for `LibraryError`.
- Lint `repeat(s, 3)` for every symbol with a through path, and report the C1 outcome.

## D42. The toolkit is `symdef`, version 0.4.0 (SYMDEF SD1)

Decided: the distribution and the import are both `symdef`; the first release under the name is
0.4.0, continuing the line of `graphical-symbols` 0.3.0. The package folder is `src/symdef`, the
repository URL in `pyproject.toml` is `https://github.com/OleJBondahl/symdef` (GitHub redirects
the old URL). Earlier entries keep the old name as they were written.
Why: a short name that is free on PyPI, one name for repository, distribution and import.
Cost if wrong: another rename of the same shape; consumers change their pin and imports once more.

## D43. `requires-python = ">=3.14"`, tested on 3.14 in `just ci` (SYMDEF SD2)

Decided: the package supports Python 3.14 and later. Development stays on 3.15 (`.python-version`,
ruff and ty targets). `just ci` ends with `just test314`: `uv run --python 3.14 --isolated pytest
--no-cov`, a throwaway environment, so the promise cannot rot. Proof it can fail: a 3.15-only line
(`lazy import json`) in `src/symdef/units.py` makes the 3.14 run stop with a `SyntaxError`.
Why: more consumers install it; the code already ran on 3.14 (2261 tests pass).
Cost if wrong: raise the floor back to 3.15; the extra test run adds about 45 s to the gate.

## D44. Published to PyPI by trusted publishing; docs on GitHub Pages (SYMDEF SD3, reverses D41)

Decided (owner 2026-10-07): a tag `vX.Y.Z` runs `.github/workflows/publish.yml`: it checks the tag
equals the package version, builds with `uv build`, and uploads with PyPI trusted publishing and
attestations, from the GitHub environment `pypi`, with `id-token: write` and no token secret.
`.github/workflows/docs.yml` deploys a minimal site (README, guide, decisions and the spec, built
by `scripts/build_site.py` with the dev dependency `markdown`) to GitHub Pages on the same tag.
Every action is pinned by full commit SHA with its version in a comment. A release is cut only
from a commit whose local `just ci` passed; no workflow runs the gate.
Why: consumers install by an exact PyPI version instead of a git tag.
Cost if wrong: delete the workflows and yank the release; the git tag install still works.

## D45. Optional `package` key in `library.toml` (SYMDEF SD8, amends D8)

Decided: `library.toml` may carry `package = "name"`, the data package's folder under `src/`
(letters, digits and `_`, not starting with a digit; anything else is a `schema` finding at
`/package`). `LibraryConfig` gains `package`, empty by default. `Library` does not change:
section 11 of the spec fixes its fields, and a test pins them. `write_build` and `stale_build`
already take the repo root, so they read the key from `root/library.toml` and pass it to
`build_files(library, package)`; a root without a readable `library.toml` gets the folder D8 makes
from the standard. This is the fix D8 named for itself.
Why: a data package whose folder is not its standard's squashed name (`electrical_symbols` for
`IEC 60617`) needs a way to say so.
Cost if wrong: drop the key; the default rule is unchanged. A library built in memory and written
to a root with no `library.toml` cannot name its folder.

## D46. A set declares its own vocabulary and required slots (SYMDEF SD6 and SD7)

Decided: `library.toml` gains `[vocabulary]` (`path_kinds`, `potentials`, `links`, each a list of
strings; a missing list is empty) and `[rules] required_slots` (for example `["tag",
"marking.<port>"]`, where `<port>` means one slot per port). The toolkit has no built-in list.
A symbol file using a path kind, node potential or `via` link not on its list fails to load with a
`schema` finding that names the word, the file and the line (the first line that quotes the word;
line 1 if the word is spelled with an escape). The check runs in `load_library`, which has the
file text. The closed enums `PathKind` and `Potential` are gone from `symdef.__all__`:
`Path.kind` is a `str` and `Node.potential` is `str | None`; JSON output is unchanged. The
structural check and `schema/symbol.schema.json` accept any string there. `Vocabulary` is a new
public name; `LibraryConfig` and `Library` gain `vocabulary` and `required_slots` (empty by
default); `lint(symbol, required_slots=())` takes the duty list, and a bundle carries neither.
The pole-pitch multiple-of-4 rule stays fixed. `[vocabulary]` and `[rules]` are strict tables: an
unknown key is a `schema` finding on `library.toml`.
Why: a set for another domain (pipes, ISA instruments) needs its own words and duties; the
toolkit supplies mechanism, not policy.
Cost if wrong: a consumer of `PathKind` or `Potential` compares strings instead; a set that
declares nothing cannot use any path kind.

## D47. The surface is every name the docs call; the schema ships in the wheel (SYMDEF SD10 and SD11)

Decided: `RULES` and `finding_key` join `symdef.__all__` (and `finding_key` joins
`symdef.lint.__all__`), and a test reads the python blocks of the README and the guide and fails
for any `from symdef... import name` whose name is not in that module's `__all__`.
`schema/symbol.schema.json` moves to `src/symdef/schema/symbol.schema.json`, so the wheel carries
it, and gains `"$id": "https://olejbondahl.github.io/symdef/symbol.schema.json"`; the docs site
publishes the same file at that address. An editor that reads a `#:schema` line then completes and
checks a symbol file as it is typed. The schema checks structure only; the declared words stay a
load check (D46).
Why: a user should find every documented name on the surface, and an editor needs a schema it can
fetch.
Cost if wrong: move the file back; the `$id` is only an address.

## D48. The newcomer's path: `symdef init`, `build` and `check` (SYMDEF SD9)

Decided: a command line `symdef` (`[project.scripts]`, also `python -m symdef`) with three verbs
on a folder, each also a function: `init(root)` writes `library.toml`, one symbol
(`symbols/resistor.toml`) and `.gitattributes` with LF line ends, and refuses a folder that already
holds any of them; `build(root)` loads, lints and writes `build/` and the bundle, raising
`LibraryError` and writing nothing if a file fails to load or lint reports an error;
`check(root)` returns the findings of the gates every set needs and never raises for a bad set.
The starter texts live in `symdef.starter`, are written by code and are loaded, linted and built
by a test, so they cannot drift from the format. Both starter files open with the `#:schema` line
of D47. The command exits 0, 1 when it found problems, 2 on bad usage, and prints each distinct
finding once.
`check` runs: files load and resolve (a number equals its file stem and fits `number_pattern`
there); every symbol lints clean, warnings included; a symbol with a through path lints clean as
`repeat(symbol, 3)`; the build is not stale (`stale-build`); the packaged bundle holds the source's
symbols (`bundle-differs`) and they lint clean. These are the generic gates 1 to 6 of the first data
package's gate file. The bundle already lives in its package (D45), so no relocation exception is
left.
The functions are `symdef.init`, `symdef.build` and `symdef.check`. `build` would shadow the
module `symdef.build`, so that module is renamed `symdef.files`; it stays the impure shell with
`project`, `cli` and `__main__`, which `scripts/fp_purity_gate.py` lists.
Why: a newcomer needs a first working set in three commands, and a test needs one call for every
gate.
Cost if wrong: drop the verbs; the renamed module only matters to code that imported
`symdef.build`, which was not on the public surface.

## D49. `deal` is removed; an AST purity gate replaces it (SYMDEF SD12, amends D36)

Decided (owner 2026-10-07): "remove deal from symdef, as we dont want to bug people with a non dev
dependency that is not integral, we should instead just write in the claude and readme that such
and such parts of the library is pure". `deal` leaves completely: no runtime or dev dependency, no
`@deal.pure`, no `import deal`. The wheel has no dependency.
`scripts/fp_purity_gate.py` now checks purity with the standard library's `ast`, over every module
under `src/symdef/` except its `IMPURE_MODULES` (`files.py`, `project.py`, `cli.py`, `__main__.py`
and the top-level `__init__.py`). In a pure module it fails on a call to `print`, `input`, `open`,
`exec` or `eval`; an import of `time`, `datetime`, `random`, `secrets`, `os`, `io`, `shutil`,
`subprocess`, `socket`, `tempfile`, `logging`, `sys` or `pathlib`; a `global` or `nonlocal`
statement; and an assignment, `del` or mutating call (`append`, `update`, ...) that writes into a
name bound at module level. Every kind has a test that makes it fire. Two probes against the real
tree: a `print()` added to a pure function reports `calls print()`; a list appended to at module
level reports `mutates module state`. The README says which modules are impure and why.
The gate is weaker than `deal.pure` in one way: it cannot prove a function raises nothing, and
the runtime wrapper also caught that. `repeat`'s two `deal.pre` preconditions are now a documented
`ValueError`; the tests that expected `deal` errors expect `ValueError`. It is stronger in two:
it also forbids file I/O and the clock, and it runs on code no test reaches. The totality of
rendering stays covered by `tests/test_svg_total.py`.
The `TC001`/`TC003` ruff ignore stays. Its stated reason was `deal`'s `inspect.signature` call,
but with `deal` gone ruff's unsafe fixes for those rules still fail: they write `lazy import`
statements, a `SyntaxError` on 3.14, and 35 test modules failed to collect. The comment in
`pyproject.toml` now says that.
Why: users should pay for nothing they did not ask for (lint was 2.6 times slower with the
contracts on, the import 13 ms slower, and the package carried a 1.9 MB dependency).
Cost if wrong: purity is proved statically only; a function that raises by accident is found by
tests, not by a wrapper.

## D50. The docs site is built by Zensical; a gallery set ships in `docs/` (SYMDEF SD13)

Decided: `scripts/build_site.py` (run by `just site` and by `docs.yml` on a tag) stages the README
as the home page, `docs/TUTORIAL.md`, `docs/GUIDE.md`, `docs/DECISIONS.md`, a generated gallery of
`docs/tutorial-set/` and a generated API reference (every name of `symdef.__all__` with its
signature and docstring) into the gitignored `.site-src/`, and builds it with Zensical (dev
dependency, `zensical==0.0.68`, the latest stable) in `--strict` mode, so a broken link fails the
build. The interface spec and the JSON schema are published at the site root, the schema at its
`$id`. `tests/test_site.py` proves a broken link fails the build; `tests/test_tutorial.py` runs
every `symdef` command, edit step and python block of the tutorial in an empty folder. The
`markdown` dev dependency goes. The gallery set is the six IEC fixtures, plus a gate valve, a pump
and a check valve drawn here (S90001 to S90003, path kind `pipe`, which shows a set declaring its
own word). S00254 carries `pole_pitch = 8`, the fix D-concern C1 names, because `symdef check`
refuses the fixture's pitch overflow; the other five files are byte-equal to the guide fixtures.
No page names a user of the toolkit. The README carries the provenance line for every IEC-style
example: original drawings, `unverified`. Both workflows run on `ubuntu-24.04` with an exact uv
version.
Why: the site must cover everything a newcomer needs, with no other repository to read.
Cost if wrong: Zensical is pre-1.0; the staged Markdown also builds with MkDocs.

## D51. The interface spec is amended in place for 0.5.0 (SYMDEF SD14)

Decided (owner C1): `SYMBOL_INTERFACE.html` opens with a dated change list and changes only
through a designer-approved spec, with a dated entry in that list and in this file. This amendment
records D45 to D49 in it: declared words and required slots (sections 5, 6, 7, 9, 11 and 12), the
API list (`Vocabulary`, `init`, `build`, `check`, `lint(symbol, required_slots)`, `Library`'s two
fields; `PathKind` is gone), the schema location, the generic layout and gates of section 12, no
runtime dependency, and a rewrite of sections 1, 12 and 13 that names no predecessor and no user.
Section 14's open items stay. The byte-equality test of the guide's code blocks passes against it.
Why: the spec was the one file still describing the first design.
Cost if wrong: revert the file; code and tests do not read its prose except the code blocks.

## D52. The mm output: to_fragment_mm beside to_fragment (SYMDEF-MM)

Decided: `to_fragment_mm` is a new public function in a new module, `svg_mm.py`, beside
`to_fragment`. It is not a keyword on `to_fragment`: `to_fragment`'s contract is module units with
the caller scaling, and one function with two units and a mapping argument would blur it.
Signature: `to_fragment_mm(symbol, *, module_mm, weights_mm, dash_mm, font_family, font_mm,
cap_ratio) -> str`. Every coordinate and radius is multiplied by `module_mm`. Stroke widths come
from `weights_mm`, one entry per `Weight`; a missing weight raises `KeyError` naming it. Dash
lengths come from `dash_mm`. Text is drawn at `font_mm` and ignores `Text.height`; its baseline is
`y * module_mm + cap_ratio * font_mm / 2`. The caller passes the font family. There is no
transform and no scale. `to_svg` and `to_fragment` bytes are unchanged; the golden fixtures under
`tests/fixtures/svg_golden` prove it. Release 0.6.0.
Why: the owner wants every size set in millimetres and rendered exactly, with nothing scaled.
Cost if wrong: the function is additive; remove it and its export.

## D53. stretch(): a cut line moves everything beyond it

Superseded in part by D67 (0.10.0): "at most one per axis" no longer holds; D69 changes how slots move.

Decided: `Symbol.stretch` holds at most one `Stretch(axis, at)` per axis, written `[[stretch]]` in a
file and `stretch` in the resolved JSON (written only when set, so existing bundles keep their
bytes; the bundle schema version stays 1). `stretch(symbol, axis, length, offsets=None)` in the new
`stretch.py` moves every point whose coordinate is greater than `at` by `length` minus the body
extent (`body_box`) along the axis: line and polyline points, ports, anchors and slots; a circle,
arc or text lying wholly beyond the cut moves whole, one wholly before it stays, one across it
raises `ValueError`. Offsets place each named port, its bound lead and its `marking.<port>` slot at
a coordinate inside the stretched body on the 1 M wiring grid; the port must face across the axis
(N or S for x, E or W for y), and an offset naming no port raises `ValueError` too. A `length`
equal to the natural extent is allowed. The result drops that axis's stretch, so a frame is
stretched on both axes by two calls; no extra API. `orient`, `translate` and `repeat` carry
the field unchanged and do not raise; the stretch is applied before them. The lint driver does not
clear it: every rule ignores it except `stretch-cut` (D55), which runs once on the base symbol. A
composite does not inherit its parts' stretch; its own `[[stretch]]` is its own. `crosses_cut` is
the one predicate the function and the lint rule share.
Why: the owner chose the stretch value: layout passes one length and symdef builds the symbol.
Cost if wrong: the field, the function and the schema key are additive; remove them and the export.

## D54. table(): rows with their own ports and slots

Decided: `table(row, n, axis, head=None)` in the new `table.py` returns `n` copies of `row`, copy k
(from 1) stepping by the row's body extent (`body_box`) along the axis. Ports, bound leads, nodes
and paths are prefixed `<k>.`, through the helpers `repeat` uses (now public in `repeat.py` as
`pole_elements` and `pole_parts`). Every slot of every copy is kept: `marking.<port>` becomes
`marking.<k>.<port>`, any other `<id>` becomes `<k>.<id>`. No through path is needed. The cap is
`repeat`'s 64, now the constant `MAX_REPEAT` in `repeat.py` (the resolver imports it). The result
keeps the row's `pole_pitch`, takes copy 1's anchors and has no stretch. A head keeps its own ids
and comes first in the lists; with a stretch on the table's axis it is first stretched to
`n * step`, the rows' total extent on that axis (amendment 2: this is how a cable head spans its
k columns stepping along x). A head with no stretch on the axis is not stretched. The head stays
where it is authored, relative to row 1, as built, and is never translated. `repeat` is unchanged.
Why: a table is cells with their own text, not poles of one device.
Cost if wrong: additive; remove the module and its export. A head that must move is a later keyword.

## D55. Lint rule stretch-cut and the schema key

Decided: a second rule beyond the spec's 33, `stretch-cut` (after `lead-off-port`, D40): group
Geometry, severity error, not orientation dependent, so it runs once on the base symbol and
`lint_allow` may exempt it. It reports, at `elements[j]`, a circle, arc or text a cut crosses
(`crosses_cut`, the predicate `stretch` itself uses), and, at `stretch[i]`, a cut that does not satisfy
`body_min <= at < body_max` on its axis (a cut at the far edge moves nothing; one at the near edge
is legal) and every stretch after the first on one axis. The rule count is 35. `symbol.schema.json`
gains `stretch`, an array of `{axis, at}`, both required, `axis` one of x and y; the file's `schema`
integer does not step, as for `port` on a line (D40). Under `orient` the lint driver leaves the
field alone; no other rule reads it.
Why: a symbol whose cut crosses a circle cannot be stretched, and the error should surface at lint, not
at the consumer's build.
Cost if wrong: the rule is additive; remove its row, check and the 35 in the counts.

## D56. Wire styles and wire()

Decided: a symbol set declares wire styles in `library.toml` as `[[wire]]` with `id`, `weight`
(`normal` or `thick`) and `style` (`solid` or `dashed`); the table is optional, and a missing key, an
unknown word or a duplicate id is a finding like those of `[vocabulary]`. `WireStyle(id, weight,
style)` is a new public dataclass; `LibraryConfig` and `Library` gain a last field `wires`.
`wire(library, style_id, points)` in the new `wire.py` returns an element-kind symbol of one open
`Polyline` of that style (name `wire <id>`, reference number `wire.<id>`), with no ports or slots;
points may be `Point`s or (x, y) pairs. An unknown id raises `KeyError` naming it (as
`to_fragment_mm` does for weights), fewer than two points `ValueError`. The consumer reads a
bundle, not the TOML, so `bundle.json` carries an optional top-level `wires` array, written only
when the library has wires (existing bundles keep their bytes; the bundle schema stays 1), checked
by `validate_bundle` and read by `library_from_bundle`. A junction dot is an ordinary symbol.
Why: the owner ruled that wires are symdef functions and layout names only a style and points.
Cost if wrong: additive; remove the module, the dataclass, the field and the bundle key.

## D57. Tint fill

Decided: `Fill` gains `TINT = "tint"`. A file may write `fill = "tint"` on a closed polyline only;
on a circle or an open polyline it is a `schema` finding, and the JSON schema agrees (a separate
fill definition for polylines, with `closed = true` required beside `tint`). `to_svg`, `to_fragment`
and `to_fragment_mm` take a keyword-only `tint: str | None = None`, the colour string the caller
chooses, drawn as the fill of every tinted shape; with `None` a tinted shape draws `fill="none"`.
The toolkit chooses no colour. So that no value can inject SVG, a colour must be `#rgb`,
`#rrggbb` or a letters-only name; anything else raises `ValueError`, whether or not a shape uses
it (`check_tint` in `svg.py`, shared by the mm output). Output bytes without a tinted shape do not
change; the golden fixtures prove it.
Why: the consumer passes the colour, as it passes slot texts.
Cost if wrong: additive; remove the enum member, the keyword and the check.

## D58. The interface spec is amended in place for 0.7.0

Decided (owner C1; model D51): `SYMBOL_INTERFACE.html` gets a dated change-list row, 2026-10-15,
0.7.0, and the sections that define the new pieces change in place: section 4 (`[[stretch]]`,
`fill = "tint"`), section 7 (`stretch` and `table` beside `repeat`), section 9 (the rule table and
count, 35), section 10 (the optional `stretch` key and the bundle's `wires`) and section 11 (the
API list, `[[wire]]` of `library.toml`, `tint`). `docs/GUIDE.md` gains "Stretching and tables";
its Python blocks run in `tests/test_readme.py`. The `[[wire]]` and `wires` bundle key are the
toolkit's own additions beyond the spec's data model, recorded in D56. The version bump, tag and
release are not part of this change.
Why: the spec is the one design document and must describe what the code does.
Cost if wrong: revert the file; code and tests read only its code blocks and the rule table.

## D59. `leads(symbol, ports)`

Decided: a public free function in `leads.py`. It removes every `Line` whose `port` is not None
and not in `ports`; every other element stays in order, and so does every other field. A listed
id that names no port of the symbol raises `KeyError` naming it; a listed port with no bound lead
is fine. Ids are those the symbol holds, so `1.a` after `table`. The caller passes the wired ports:
symdef knows no net.
Why: a router draws a stub only for a wired port, and a symbol's file cannot know which.
Cost if wrong: additive; remove the module, the export and the test.

## D60. `Style.DASH_DOT` and `dash_dot_mm`

Decided: `Style` gains `DASH_DOT = "dash_dot"`, accepted wherever `dashed` is: element `style`, a
`[[wire]]` style, the loader, the JSON schema and the serialized form. `to_fragment` draws module
units `1 0.25 0.0625 0.25` (the spec fixes none; chosen as a long dash, then a dot of a quarter of
a gap's length). `to_fragment_mm` gains `dash_dot_mm: tuple[float, float, float, float] | None =
None` after `dash_mm`; drawing a dash-dot element while it is None raises `ValueError` naming the
keyword, and a symbol with none never asks for it. Output without the style is byte-identical.
Why: the style words are the file's, the lengths are the caller's, as for `dash_mm`.
Cost if wrong: additive; remove the member, the keyword and the schema entries.

## D61. `muted`

Decided: `to_fragment` and `to_fragment_mm` gain a keyword-only `muted: str | None = None`, the
colour of a symbol drawn as not installed (designer ruling, amendment 3: the caller's colour, as
`tint` is, not a fixed grey). It is checked like `tint` (`check_colour`, shared); a bad value raises
`ValueError` whether or not it is used. Muted draws the group stroke, every text and every solid or
tint fill in that colour; every line style becomes a dash and a gap each of the normal stroke width
(`Weight.NORMAL.value`, or `weights_mm[Weight.NORMAL]` in mm, a `KeyError` if absent); a text has no
stroke and no dash; an unfilled shape stays unfilled. `dash_mm` and `dash_dot_mm` are then not
read. With `None` the bytes are those of 0.7.0.
Why: one look for a thing that is not installed, with the colour a drawing convention of the caller.
Cost if wrong: additive; remove the keyword and the helper.

## D62. The interface spec is amended in place for 0.8.0

Decided: `SYMBOL_INTERFACE.html` gets a change-list row (2026-10-15, 0.8.0); section 4 names
`dash_dot` and its pattern, section 7 gains `leads`, section 11 lists `leads`, `muted` and
`dash_dot_mm` and the `[[wire]]` styles. The rule count stays 35. `docs/GUIDE.md` gains "Bound
leads and muted symbols". The version bump, tag and release are not part of this change.
Why: the spec is the one design document and must describe what the code does.
Cost if wrong: revert the file; tests read only its code blocks and the rule table.

## D63. `texts` in `to_fragment` and `to_fragment_mm`

Decided: both gain the keyword-only `texts: Mapping[str, str] | None = None`. `None` gives the 0.8.0
bytes (pinned by `tests/test_slot_text_identity.py`). Otherwise one `<text>` per slot with a
non-empty string, in slot id order (`_slots_by_id`, the preview's rule), after the elements.
Alignment is the preview's: E start and W end, capitals centred on the point; N middle, baseline on
it; S middle, baseline one capital below it. One table (`SIDE_ALIGN`) feeds both functions and the
preview. `to_fragment_mm` draws at `font_mm` with `cap_ratio * font_mm` as the capital height and
never measures; `to_fragment` auto-sizes as the preview does (at most 1 M, size 0 draws nothing).
Attributes: `fill` black or the `muted` colour, `stroke="none"`, `font-family="sans-serif"` in
module units and the caller's family in mm, no `class` (designer, G6). A key that is no slot id raises
`KeyError` before anything is drawn, also for an empty string.
Why: render must not build slot text itself; the preview already fixes the baseline rule.
Cost if wrong: additive; remove the keyword, the table and the helpers.

## D64. Required slots checked when texts are drawn

Decided: both functions gain `required_slots: Sequence[str] = ()`, shaped as `lint`'s argument and
expanded by the same function (`required.required_ids`, which `slot_missing` now calls; its findings
are unchanged). A missing slot raises `ValueError` naming the symbol and the slot ids, only when
`texts` is not None; an empty string satisfies it. The `kind = "symbol"` limit of the lint rule comes
with the shared function, so another kind demands nothing here either.
Why: designer ruling G1; one rule in one place.
Cost if wrong: additive; remove the keyword and the check.

## D65. `turn = true`

Decided: `Slot.turn: bool = False` (last field), the slot key `turn` (loader, schema), written by
`serialize` only when true so a set without turned slots keeps its bytes. `box` is the footprint as
drawn; a turned string runs along its height and `to_fragment` fits it there. No new lint rule. A
turned string reads bottom-up: N starts at the point, S ends there, E and W centre on it; the
baseline sits half a capital east of the point for N and S, a capital for E and none for W, so the
glyphs lie beside the box. The text carries `transform="rotate(-90 x y)"` about its baseline
point, the one transform symdef writes (`to_fragment_mm`'s docstring says so). `orient` never
changes `turn`; `repeat`, `table`, `stretch` and a composite's slot reference keep it (they copy
slots with `replace`).
Why: designer rulings G2 to G5.
Cost if wrong: additive; remove the field, the key and the branch.
Known: the `to_svg` preview ignores `turn` in 0.9.0, so a turned slot drawn flat misleads a symbol author; the fix comes in the next release through the shared SIDE_ALIGN table (designer 2026-10-16).

## D66. The interface spec is amended in place for 0.9.0

Decided: `SYMBOL_INTERFACE.html` gets a change-list row (2026-10-16, 0.9.0), section 6 the `turn` key
and two paragraphs on drawing, section 11 the two keywords. `docs/GUIDE.md` gains "Drawing slot
text". The rule count stays 35. The version bump, tag and release are not part of this change.
Why: the spec is the one design document and must describe what the code does.
Cost if wrong: revert the file; tests read only its code blocks and the rule table.

## D67. Weighted cuts

Decided: `Stretch.weight: float = 1` (last field), the file key `weight` (a number above zero; the
loader and the schema refuse zero and below), written by `serialize` only when not 1. An axis may
carry several cuts. `stretch` sorts the axis's cuts by `at`, shares `length` minus the natural
extent among them in proportion to their weights, and moves a coordinate by the sum of the shares
of the cuts it lies strictly beyond. One cut takes `delta` itself, not `delta * w / w`, so a
single-cut result is the 0.9.0 bytes. A line or polyline across a cut grows by that cut's share; a
circle, arc or text across any cut raises `ValueError`; one wholly beyond some cuts moves by their
shares. `offsets` is unchanged and runs after the shares. `stretch-cut` loses its "second stretch
per axis" finding and gains "a second cut at the same `at`", so the rule count stays 35.
Why: designer ruling on weighted cuts (Q4, Q5). A title block needs a fixed edge and two growing spans.
Cost if wrong: additive; a file without `weight` and with one cut per axis is unchanged.

## D68. Slot side `C`

Decided: `C` is not a compass point. `Centre` (a one-member enum, `Centre.C`) and
`SlotSide = Direction | Centre` are new in `model.py`; `Slot.side` is a `SlotSide`, so `Direction`,
ports and anchors never see `C`. The loader takes `"C"` for a slot side only (its own enum), the
schema has a `slot_side` definition, and `serialize` writes `"C"`. `slot_box` of a `C` slot is `[w, h]`
centred on `position`, turned or not (`box` stays the footprint as drawn). Text aligns through the
same two tables as the other sides: `C` is ("middle", 0.5), so the baseline sits half a capital
below the point and the capital height is centred on it; a turned `C` is ("middle", 0.5) east, the
glyphs centred across the reading line. `orient` leaves a `C` side as it is and moves the point.
`repeat`, `table`, `stretch` and a composite's slot reference keep it (they copy with `replace`).
Why: designer ruling Q1 to Q3. A slot side is where text sits and a port side is where a wire
leaves; keeping `C` out of `Direction` means a port can never be `C`.
Cost if wrong: remove the enum, the schema value and the table entries.
Concern (spec): the spec asks for a lint check that a `C` slot's `position` is its box's centre. With
the box centred on `position` by definition (Q3) and `stretch` recomputing `position` as the new
centre, no stored slot can fail it. No such check is in 0.10.0 pending the designer's ruling.

## D69. Slots follow the cuts

Decided: `stretch` moves each corner of a slot's box and its `position` by the shares of the cuts
they lie beyond (`stretch_slot.py`). A box across a cut grows by that cut's share, and the stored
`position` and `box` are recomputed so `slot_box` of the result is exactly the moved corners: the
side's own edge follows its corner, and the centred axis takes the middle of the moved corners. A box
whose two edges move alike keeps its `box` and its position moves as in 0.9.0 (same bytes). A turned
slot grows along its authored `box`. The room a slot has after stretching is the
stretched symbol's `slot_box`.
Why: designer ruling; a slot that spans a cut must grow with the body.
Cost if wrong: a symbol with a slot across a cut changes size; every other output is unchanged.

## D70. `between` elements

Decided: `Line.between` and `Polyline.between` (last field, default false), the file key `between`
on those two element tables only (a circle, arc or text with it is a schema finding), written by
`serialize` only when true. `table(row, n, ...)` draws a `between` element of the row in rows 1 to
n-1 and leaves it out of row n, so n = 1 draws none. The head is unaffected: a `between` element in a
head is drawn as authored, and so is one on a lone symbol. `repeat` and `translate` keep the flag
(`replace`). A table without a `between` element is byte-identical to 0.9.0.
Why: designer ruling; a strip has one tick fewer than it has cells.
Cost if wrong: additive; remove the field, the key and `_row_elements`.

## D71. The interface spec is amended in place for 0.10.0 (D67 to D70)

Decided: `SYMBOL_INTERFACE.html` gets a change-list row (2026-10-16, 0.10.0), the `stretch` and
element keys in section 4, side `C` in section 6, the stretch and table paragraphs in section 7, the
`stretch-cut` row in section 9 and the types in section 11. `docs/GUIDE.md` gains "Weighted cuts,
moving slots and ticks between rows". The rule count stays 35. The version bump, tag and release
are not part of this change.
Why: the spec is the one design document and must describe what the code does.
Cost if wrong: revert the files; tests read only the code blocks and the rule table.

## D72. A non-C slot keeps its position across a cut (0.10.1)

Decided: `stretch_slot` moves the `position` of every slot but `C` by its own shift, the shares of
the cuts it lies beyond, as in 0.9.0, and grows `box` by the difference of its edges' shifts. Only a
`C` slot is placed at the middle of its moved edges (D68). So a W, E, N or S box across a cut
grows while its position stays where 0.9.0 put it; `slot_box` of such a result is centred on the
position on the centred axis and is no longer the moved corners there. 0.10.0 re-centred every
side, which moved the text of `marking.<port>` slots across a cut.
Why: designer spec (position moves with the cuts it lies beyond, D69; only `C` is centred, D68);
found by a byte check against 0.9.0.
Cost if wrong: a non-`C` slot across a cut sits at its box centre again; revert `_place`.

## D73. Font metrics are library data (0.11.0)

Decided: `library.toml` takes an optional `[font]` table with `units_per_em`, `cap_height`,
`ascent`, `descent` and `default_advance` (numbers above zero, all required), an optional
`thick_factor` (default 1: what an advance is multiplied by for `Weight.THICK`) and a required
`[font.advances]` table of one number per single character. `bundle.json` gains an optional `font`
object of the same keys, `advances` an object, written only when the library has a font, with
`thick_factor` only when it is not 1. `Library.font` and `LibraryConfig.font` are
`FontMetrics | None` (frozen, slotted, in `symdef.font`), `None` when none is declared.
`text_width(font, text, height, weight=Weight.NORMAL)` is the sum of the advances in ems times
`height`; a character not in `advances` takes `default_advance`; with `font=None` it is 0.6 em
per character, the measure of 0.10.1, computed in the same order so existing output is
byte-identical. `body_box`, `keepout_box` and `element_box` take `font=None`. `cap_height(font,
height)` is the capital's height in module units (0.72 em with no font). The font is data in the
library, never global state; kerning, ligatures and per-weight advance tables are not modelled.
Why: font metrics are symdef library data, as the rest of the library is.
Cost if wrong: the keys are additive and optional; remove `font` from the two dataclasses, the
loader and the bundle, and `font=None` from the three box functions.

## D74. Slot text: `slot_text`, `slot_box` with a text, `TextPlacement` (0.11.0)

Decided: the module `symdef.slottext` holds `SIDE_ALIGN` and `TURNED_ALIGN` (moved out of `svg`,
which reads them from there) and `slot_text(slot, text, height, font) -> TextPlacement(point,
anchor, turned)`. `point` is the baseline point: the slot point shifted by the table's number in
cap heights (south for an upright slot, east for a turned one); `font` gives the cap height, and
`None` gives 0.72 em. `text` does not move the point, since the anchor does the aligning; it is
in the signature as the ruling gives it. `slot_box(slot, text=None, height=None, font=None)` with
no text is the reserved box of 0.10.1; with a text it is the union of the reserved box and the
string's extent (its measured width by one cap height, upright from the anchor, or turned
bottom-up with the caps to the west of the point). A text without a height raises `ValueError`.
Why: the caller reads slot text placement from symdef, not its own copy.
Cost if wrong: additive; the new parameters default to the old behaviour. Revert `slottext.py`
and the three parameters.

## D73 amended: the library's settings are `[font]` and `[grid]` in `library.toml`

Decided: the `[font]` table of D73 also takes a required `name` (a string; it changes no
measure), and `library.toml` gains an optional `[grid]` table with `module_mm` (a number above
zero) and `divisions_per_module` (an integer power of two, so a division is exact in floating
point and the off-grid test stays an exact multiply). `Grid(module_mm, divisions_per_module)`
(frozen, slotted, in `symdef.units`, with `division` = 1 / `divisions_per_module`) is
`Library.grid`; a library with no `[grid]` has `DEFAULT_GRID`, 2.5 mm and 8 divisions, which are
`DEFAULT_MODULE_MM` and `GRID_DIVISION` of 0.10.1, so every constant keeps its value. The bundle
gains an optional `grid` object, written only when the grid is not the default, so existing
bundles stay byte-identical. `lint(symbol, required_slots=(), grid=DEFAULT_GRID)` and
`off_drawing_grid(symbol, grid=DEFAULT_GRID)` check the drawing grid against the library's own;
`check` and `build` pass `library.grid`. The wiring grid (`port-off-wiring-grid`) is a separate
rule and is unchanged. `to_fragment_mm` keeps its `module_mm` keyword; a caller passes
`library.grid.module_mm`.
Why: one settings file, frozen in the loaded library.
Cost if wrong: both tables are optional; revert `Grid`, the two keys and the `grid` argument.

## D75: grid divisions are helpers that take the grid

Decided: `to_divisions(grid, v) -> int`, `from_divisions(grid, n) -> float` and
`ceil_divisions(grid, v) -> int` in `symdef.units`, exported. The grid comes first, as the amended D73 rules;
there is no public `DIVISIONS_PER_MODULE` constant, a caller reads `grid.divisions_per_module`.
`to_divisions` raises `ValueError` naming the value (`repr`) when `v` is not a whole number of
divisions, and for NaN or infinity. `ceil_divisions` is the one round-up rule: it counts a value
within 1e-9 divisions above a multiple as that multiple, so float noise from a measured extent
adds no division. `GRID_DIVISION` and `snap` stay unchanged.
Why: the grid is library data, so the helpers take it.
Cost if wrong: additive. Move the tolerance by editing `_DIVISION_TOLERANCE`; remove the three
functions to revert.

## D76: turning helpers are public; `orient_box` turns a box about the origin

Decided: `orient_point` and `orient_direction` join `__all__`, and `orient_box(box, orientation)
-> Box` is new in `symdef.orient`. It turns the box's two corners as points (mirror x first for an
MR orientation, then clockwise quarter turns) and re-bounds them, about the symbol's origin, as
`orient` does. For any symbol and all eight orientations `orient_box(body_box(s), o)` equals
`body_box(orient(s, o))`; a test asserts it on a non-square symbol.
Why: a caller turns a box once, in symdef, not by its own copy of the maths.
Cost if wrong: additive; remove `orient_box` and the two exports.

## D77: small accessors, and `nodes_of` public

Decided: `Box.union(*boxes)` (a static method; one box gives itself, none raises `ValueError`),
`slots_box(symbol)` (the union of the slots' reserved boxes without the body; the origin box when
there are no slots), `pole_pitch(symbol)` (the effective pitch: the symbol's own, else the default
4 that `repeat` already uses, imported from one constant) and `pole_port(k, port_id)` (the id a
port takes in pole `k`, `"<k>.<port_id>"`; `repeat` now builds every pole id through it). All four
and `nodes_of` (every node, the declared ones then one per unlisted port) join `__all__`, each with a
docstring and a test.
Why: the caller reads these facts from symdef, not a copy.
Cost if wrong: additive; `repeat`'s output is byte-identical (the tests of D0 to D72 stay green).

## D78: a loaded library's symbols are read-only

Decided: `load_library` and `load_bundle` wrap `Library.symbols` in a `MappingProxyType`, so
assigning into it raises `TypeError`. The field is typed `Mapping[str, Symbol]` (it already was);
no writer of `.symbols` exists in the repository. A `Library` built by hand keeps whatever mapping
its caller passes.
Why: a library is a frozen value, as the other records are.
Cost if wrong: a caller that edited a loaded library's symbols must copy them first; drop the wrap
to revert.

## D79: the grid helpers read the grid, and `Grid` checks itself

Decided: `Grid.__post_init__` raises `ValueError` naming the value and the fix when
`module_mm` is not a finite number above zero or `divisions_per_module` is not a power of two; the
two rules are `units.module_error` and `units.divisions_error`, and the loader's `[grid]` checks
call them, so there is no second copy. `snap(v, grid)` and `on_grid(v, tol, grid)` take the grid as
a trailing argument (as `lint` does), defaulting to `DEFAULT_GRID`; a call without a grid is
byte-identical to 0.10.1. `FontMetrics.advances` and `SIDE_ALIGN`/`TURNED_ALIGN` are read-only
mappings (`MappingProxyType`). This replaces D75's "`snap` stays unchanged".
Why: a library's grid is data, so every grid function must read it; a grid that is built by hand
must not be able to hold an inexact division; frozen records hold no mutable contents.
Cost if wrong: additive for callers; drop the trailing argument to revert.

## D80: symdef raises its own errors

Decided: the base error is `SymdefError` (renamed from `GraphicalSymbolsError`, no alias). Under it
sit `InvalidValueError` (a bad argument or malformed data; replaces every `ValueError` raised by
symdef), `UnknownNameError` (a name not in the set it was looked up in; replaces every `KeyError`),
`UnknownSymbolError` and `LibraryError`. They are plain subclasses: none inherits the builtin it
replaces, so `except ValueError` no longer catches symdef. A message gives the cause, the value
and the valid values or the fix. No `FileError`: symdef raises no `OSError` itself, the reads and
writes of `files` let pathlib's own propagate and the docstrings say so; `project.init` raises
`InvalidValueError` for an existing file (review round 1; it first kept `FileExistsError`). The
`OSError` that `write_build` and `stale_build` let propagate (disk errors) is a documented exception. `to_fragment_mm`
raises `UnknownNameError` (not a bare dict `KeyError`) for a weight missing from `weights_mm`.
`tests/test_errors.py` walks the package with `ast` and fails on a raise of any builtin
exception class. The loader's own `except ValueError` clauses around standard-library
parsers stay.
Why: one base to catch, named causes, and a clean break while there are no other callers to keep.
Cost if wrong: a consumer that caught the builtins must catch `SymdefError` or the subclass; add a
second base to a class to revert one.

## D82: `measure`, and the font holds one advance table per weight

Decided (font part, committed first): `FontMetrics.advances` is a read-only mapping from `Weight`
to a read-only mapping of character to advance, one table for every `Weight`; a font missing one
raises `InvalidValueError` naming it. `thick_factor` is removed. `text_width` reads the table of the
weight it is given, so a bold text differs glyph by glyph from a regular one. `library.toml`'s
`[font]` takes `[font.advances.normal]` and `[font.advances.thick]`, both required, each a table of
single characters to numbers above zero; the bundle's `font.advances` is an object with the keys
`normal` and `thick`, each such a table. `default_advance` stays one number for both.
Why: a bold face is not a scaled regular face, so a factor mismeasures it.
Cost if wrong: a library with a font must write a second table; a bundle written by 0.11 does not
load (its `advances` is flat). Fonts were new in 0.11, so the break is free.

## D81: `GridPoint`, `GridBox` and `GridPort` are their own types

Decided: `symdef.gridtypes` holds three frozen slotted types whose coordinates are whole grid
divisions: `GridPoint(x, y)`, `GridBox(min, max)` with `width`, `height` and `GridBox.union`
(the shape of `Box.union`), and `GridPort(id, x, y, direction)`. A coordinate that is not an `int`
(a `bool` too) raises `InvalidValueError`. They do not subclass `Point` or `Box`.
Why: divisions are a second unit; a float-typed `Point` could carry either unit unnoticed.
Cost if wrong: additive; drop the module to revert.

`measure(symbol, orientation, library, texts=None, text_height=None) -> Measure` (module
`symdef.gridmeasure`, so the function does not shadow its own module). It orients the symbol, then
reads `body_box`, `slot_box` (with `library.font`) and the ports, and returns a frozen `Measure`:
`body`, `keepout` (the body united with every slot box, text included) as `GridBox`; `slots` as id
to `GridBox`; `ports` as id to `GridPort` with the direction after the turn; `slots` and `ports`
are read-only. Choices: slot text comes from the optional `texts` (slot id to string) with
`text_height`; a text given without a height raises `InvalidValueError` naming `text_height`, a
key that is no slot raises `UnknownNameError`; a slot with no string is its reserved box. An
extent rounds outward (`min = -ceil_divisions(-min)`, `max = ceil_divisions(max)`), so a body
already on the grid is exact; a port is a position and goes through `to_divisions`, so an off-grid
port raises naming the port and the value. A slot's text is measured in the normal weight; a body
`Text` uses its own weight's table.
Why: SB12: layout gets the data from symdef and converts nothing.
Cost if wrong: additive; delete the module and the exports to revert.

## D83: `to_placed_fragment` draws a symbol at a grid position

Decided: `to_placed_fragment(symbol, orientation, at, library, *, tint, muted, texts,
required_slots)` in `symdef.svg_placed` orients the symbol, draws it with `to_fragment`, and wraps
it in one `<g transform="translate(X Y)">`, X and Y being `at` (a `GridPoint`) turned into module
units by `from_divisions(library.grid, n)`. `to_fragment`, `to_fragment_mm` and `to_svg` are
unchanged, so every golden is byte-identical; `to_fragment_mm` is listed in the changelog for
removal in 0.13, once its callers use the placed call.
Why: SB12: the renderer places a symbol with no unit conversion of its own.
Cost if wrong: additive; delete the module and the export to revert.

## D84: two doors, `symdef` for consumers and `symdef.authoring` for authors

Decided: `symdef.authoring` holds nine names: `build`, `check`, `init`, `lint`, `write_build`,
`stale_build`, `RULES`, `finding_key` and `LibraryConfig`. They leave `symdef.__all__`; the two
`__all__` sets are disjoint and `from symdef import build` raises `ImportError`. The rule: a name
goes to the author door when no consumer-side call takes or returns it. Fransys's import census
(2026-10-16) found no consumer import of these nine. `LibraryError` stays on the consumer door:
`load_library` and `load_bundle` raise it. `Finding` and `Severity` stay there too, since they ride
on `LibraryError.findings`; so does `Status`, a `Symbol` field a consumer building one sets. The
`symdef` CLI imports from `symdef.project`, unchanged. `symdef.authoring` only re-exports, so the
purity gate needs no entry for it.
Why: a consumer's surface is what it draws with; the authoring verbs are noise there and a second
reason for a major bump when one changes.
Cost if wrong: breaking for an author who imports from `symdef`: change the import path.

## D85: a surface snapshot and a changelog

Decided: `surface.toml` at the repo root lists, sorted, the `__all__` of `symdef` and
`symdef.authoring`; `scripts/write_surface.py` writes it and `tests/test_surface.py` fails on any
difference. `docs/CHANGELOG.md` has one section per version, newest first, with one line per name
added, removed, moved or widened. `tests/test_changelog.py` requires a section for
`LIBRARY_VERSION`, as the newest, with a line. The rule: a `surface.toml` diff comes with a
changelog line in the same commit. The first entry is the retroactive `Slot.side` widening to
`Direction | Centre`, in 0.10.0.
Why: a consumer pins a version and needs to see what moved; the snapshot makes a silent move a
red test.
Cost if wrong: additive; delete the file, the script and the two tests to revert.

## D86: two wire pitches in `Grid`, and a map of text heights in the font

Decided: `Grid` gains `wire_pitch` (default 8) and `wire_pitch_fine` (default 4), in divisions;
`module_mm` stays the fixed symbol size. `[grid]` takes `wire_pitch` and `wire_pitch_fine` and
refuses a third pitch key (`unknown key`), a pitch that is not a whole number above zero, and a
fine pitch that does not divide the standard one. Every port of a resolved symbol must sit on the
standard pitch: `resolve_library` adds the `port-off-wiring-grid` finding (the lint rule, reused,
exempt through `lint_allow`) at load, so a library with an off-pitch port does not load.
`electrical_symbols` was measured first: 76 symbols, 117 ports, none off a 1 M pitch. `FontMetrics`
gains `heights`, a read-only map from a name to a capital height in millimetres, read from
`[font.heights]` and carried by the bundle (written only when not empty). symdef does not interpret
the names. `measure` is unchanged and takes no `module_mm`.
Why: Fransys's GRID-HOME needs the pitches and the text heights as library data. A default of 8/4
with 8 divisions is 1 M and 0.5 M; a library with 4 divisions and no pitch keys gets a standard
pitch of 2 M.
Cost if wrong: additive for a library that sets nothing; the loader check is new for one that has
an off-pitch port (set `wire_pitch` or move the port).


## D87: `measure_font`, and `[font]` may name its files

Decided: `measure_font(regular: bytes, bold: bytes) -> FontMetrics` (new module `fontmeasure`)
measures two TTFs with fontTools. The advances are `hmtx` widths for ASCII, Latin-1 and eight
symbols, the regular face for `Weight.NORMAL` and the bold face for `Weight.THICK`. `cap_height` is
the top of the glyph H, `descent` the depth of the glyph p, `ascent` the OS/2 typographic
ascender, all from the regular face. `default_advance` is the largest regular advance of the
covered set (1843 for the house face). `name` is the regular face's family name (name id 1). A face
without H or p, faces that differ in units per em, and bytes that are not a TTF raise
`InvalidValueError`; the first names the glyph. `[font]` takes either the literal metrics or
`name` and `files = { regular, bold }`, never both; `symdef build` reads the files, relative to
`library.toml`, in `files.py` and writes the measured table into the bundle. The measure takes
bytes, so symdef reads no file at runtime. `fonttools==4.67.0` is a runtime dependency, ruled by the
designer (spec SETTINGS ST5); CLAUDE.md's "no runtime dependency" line is out of date and the
designer edits it. `fontmeasure.py` is in the purity gate's `IMPURE_MODULES` only because fontTools
needs a `BytesIO`; it touches no file.
Why: a consumer font must come from its files with one function (spec SETTINGS ST5).
Cost if wrong: the tables of the house font are tested exactly against an independent copy; a
different default-advance rule moves only characters outside the covered set.

## D88: `Library.with_settings`

Decided: `Library.with_settings(*, module_mm=None, font=None, heights=None, lines=None)` returns a
replaced library. `font` is the pair of TTF bytes, measured by `measure_font`; the library's
`heights` are kept unless `heights` is given. `Grid` and `FontMetrics` run their own checks, a
height or width must be a number above zero, a wire weight needs a width, and then the rule
`text-outside-body` runs over every symbol of the result (D90, which replaced `text-too-large` here) and a hit raises
`InvalidValueError` naming the symbol. The logic is the free function `symdef.settings.with_settings`; the method delegates
through a deferred import because `settings` imports `model`. The concern that `text-too-large` reads no font was ruled in D90: `text-outside-body` measures with the font.
Why: spec SETTINGS ST4.
Cost if wrong: additive; the font-aware rule would be a lint-rule change in a later release.

## D89: `[lines]`, a width in millimetres per weight

Decided: `library.toml` takes `[lines]` with `normal` and `thick` as millimetres above zero.
`Library.lines` is a read-only `Mapping[Weight, float]`, empty when the table is absent, and the
bundle carries `lines` only when not empty, so existing bundles keep their bytes. With the table
present, a `[[wire]]` weight without a width is a load error (`lines_problems`), and
`with_settings(lines=...)` runs the same check. Nothing in drawing reads `lines`.
Why: spec SETTINGS ST4; the millimetres lived in the consumer. `Weight.value * module_mm` already
equals them (0.1 and 0.2 of 2.5 mm).
Cost if wrong: additive.

## D90: `text-outside-body`, the font-aware check that replaces `text-too-large` at build

Decided: `text-outside-body` (`symdef.lint.textbody.text_outside_body(symbol, font, module_mm)`) checks a fixed
Text anchored inside the symbol's body, the union of its non-Text elements, and requires its extent to lie wholly
inside that box, measured with the library font at the text's height and weight. A text anchored outside the body,
or a symbol with no other element, is not checked. It is a library-level check outside the per-symbol lint registry:
not one of the 35 guide-table rules, not in `__all__`: `lint()` takes no font, so a registered rule could not measure.
Two call sites run it: `load_library` (and so `symdef build`) with the library font when it has one, raising
`LibraryError` naming the symbol; and `Library.with_settings`, instead of `text-too-large`;
`text-too-large` stays for authoring.
Why: designer ruling 2026-10-16 (b), spec SETTINGS ST4 amendment 2. `text-too-large` compared height with 1 M and read
no font, so a consumer font could never fail the build.
Cost if wrong: additive; the free function can move into the lint registry later.


## D91: `measure(attach=)`, a coil's contact-table room is measured by symdef

Decided: `measure(symbol, orientation, library, texts=None, text_height=None, *, attach=None)` takes `attach`, a map of
slot id to a `Symbol`. The attached symbol's `keepout_box` size is placed at the turned slot's point and side, as a slot's
reserved box is (E grows right and W left, centred on y; N grows up and S down, centred on x; C centred both ways),
and united with the slot's box (`slot_box`, with its text when given). The result is `Measure.slots[slot_id]`, and so part
of `Measure.keepout`. As with a slot's box, only the point and side are turned with the view, never the attached box. A key of
`attach` that is not a slot id of the symbol raises `UnknownNameError` naming the key and the slot ids, as `texts`
does. An empty or absent `attach` returns exactly what `measure` returned before. The caller builds the attached symbol
with `table(row, n, "y")`, and tiers as `table(that, tiers, "y")`.
Why: designer ruling 2026-10-16 (SYMDEF-LAYER Part D Q1 a). The room for a coil's contact table is a drawn size, and
symdef owns drawn sizes (owner 2026-10-16), so the Fransys layer only copies fields.
Cost if wrong: additive; a new keyword with a default.


## D92: `FontMetrics.family`, read from the font file

Decided: `FontMetrics` has a field `family`, the family name a renderer resolves the font by. An empty `family` at
construction means `name`, so `.family` is never empty. `measure_font(regular, bold)` sets it from the regular face's name
ID 16 (typographic family), else name ID 1; `name` stays ID 1. The literal-table `[font]` form, which has no bytes, takes
an optional `family`, default `name`. The `files` form takes its family from the bytes; a `family` key beside `files` is a
schema finding saying the family comes from the font file. The bundle's `font` object writes and reads `family`.
Why: designer ruling 2026-10-16. Typst resolves a font by its typographic family (ID 16); symdef recorded ID 1, which is
"DejaVu Sans Condensed" for the house face (ID 16 is "DejaVu Sans", ID 17 "Condensed"), and Typst does not resolve it.
A family read from the bytes cannot disagree with the face that is drawn and measured.
Cost if wrong: additive; a new field with a default.

## D93: `[font]` heights beside `files`

Decided: `[font]` with `files` takes `heights`, a table of names to capital heights in mm, each above zero, beside `name`
and `files`. `LibraryConfig.font_heights` holds them between the parse and the read; `files.py` puts them on the measured
`FontMetrics.heights`. symdef does not interpret the names (D73). `family` beside `files` stays refused (D92). `heights`
and `files` without `name` is still "missing required key 'name'". Any other key beside `files` is refused with a message
that names the key and the fix: "`K` is not a key of the files form (`name`, `files`, `heights`); remove it, or drop
`files` and give the measured tables". The bundle needed no change: `heights` already round-trips.
Why: designer ruling 2026-10-16 (SYMDEF-0.16). The consumer's text sizes are not in the font bytes; the files form could not
carry them, so a files-form library had no heights.
Cost if wrong: additive; a key that was refused is accepted. The reworded error is the only changed text.

## D94: `fitted_table`, a table sized by its texts

Decided: `fitted_table(row, axis, texts, library, text_height, *, head=None, head_texts=None)` returns `table(row, len(texts), axis, head)` with each column as wide as its widest text. `texts` holds one mapping of slot id to text for each row. Each text is set in `library.font` at `text_height` (module units), and the widest over all rows and `head_texts` is rounded up to whole grid divisions. A column is a row slot with a `[[stretch]]` cut across its box on the other axis; the cut grows by the rounded width less the slot's reserved extent, never below zero, so the row's pads stay. The growth goes through `stretch`, and the head grows at the same cuts. A column never shrinks below the row's natural slot box. Errors raise `InvalidValueError` or `UnknownNameError`, each naming the thing and the fix: no font; a text height not above zero; a text for a slot the row lacks; a slot with no cut across its box; a head with no cut where the rows grow; `head_texts` without `head`.
Why: owner 2026-10-18 chose the text-sized table: the contact table's width follows its texts today, and the measure belongs in symdef, which owns the font and the drawn sizes.
Cost if wrong: additive; a new function, and nothing existing changes.

## D95: marker fit: multi-line slot text, `fitted_symbol`, closed wires

Decided: (1) `slot_lines(slot, text, height, font) -> tuple[TextPlacement, ...]` returns one placement per `\n` line. Under the default "cap" text-block rule the rows are `LINE_PITCH = 1.5` cap heights apart (one cap height and half of one more); the "grid" rule is in the Rule line below. The block is centred on the slot point across the stacking direction (south, or east for a turned slot, west to east), except that it grows away from the point on the side where the text already leaves it: N up, S down, a turned W west, a turned E east. `text_box` is the union of the lines' boxes, and `to_fragment` and `to_fragment_mm` draw one `<text>` per line; a one-line text is placed as in 0.17, byte for byte. `to_fragment`'s sample size also divides the box height by the number of lines. (2) `fitted_symbol(symbol, texts, library, text_height)` grows the cut across each named slot's box on x and on y so the slot holds its text as `text_box` measures it, rounded up to whole grid divisions, through `stretch`; it shares `_growth` and `_grown` with `fitted_table`, with a lenient mode: a text that fits needs no cut, and a slot that must grow and has no cut raises `InvalidValueError`. (3) The marker stub needs no source: `wire` already draws a port-to-marker polyline in any `[[wire]]` style, a data package names its style `marker`; a test and a guide sentence cover it. (4) `wire(..., *, closed=False)`: `closed=True` emits `Polyline(..., closed=True)` with no fill and needs three points. Measured: the same rectangle rendered through `to_fragment_mm` and cairosvg, open with a repeated first vertex against closed, at 0.8 mm, differs in a 16 px square at the closing corner (two butt caps against a mitred join), so the keyword is needed. The text-outside-body lint (D90) measures fixed `Text` elements, which stay one line; the block is measured through `slot_box(slot, text, ...)`, which uses `text_box`.
Rule: `[font] text_block = "cap" | "grid"` (default "cap", today's pitch and cap-centred baseline) sets how a text block is placed; "grid" is Fransys render's rule: row pitch = text height rounded up to whole divisions, block top snapped down to a division, baseline = top + ascent * height (Ruling 6). `slot_text`, `slot_lines`, `text_box` and `slot_box` take `grid` for it.
Why: designer ruling 2026-10-18 (SYMDEF-0.18, Ruling 5, M1 to M4): the marker drawings need a symbol fitted to its texts, multi-line slot text, a stub in a wire style, and a closed outline that joins at its corner.
Cost if wrong: additive. The only changed behaviour is a slot text containing a newline, formerly one `<text>` with the newline in it.
