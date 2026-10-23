# Changelog

What changed in the public surface of each release: a name added, removed or moved, and a type that widened. Every change to `surface.toml` has a line here. The reasons are in [the decisions](DECISIONS.md).

## 0.25.0

- Added: `tag_roots(symbol, orientation, library, *, gap, marking_height)` and `TextRoot(x, y, h, v)`: the text root of a symbol's tag slot and its three reflections through the body centre, in whole divisions of the library's grid (D113).
- Added: `em_height(font, cap)`: the text height whose capital is `cap` tall, the exact inverse of the capital height a font gives (D114).

## 0.24.1

- Added: `measure(..., *, attach=None, stretch=None)`; `stretch={axis: length}` measures the symbol as `stretch(symbol, axis, length, grid=library.grid)` would make it, without building it (D111).

## 0.24.0

- Changed: `repeat` (and a part's `repeat` key) accepts a symbol with no through path; every pole then has none (D106).
- Added: keyword-only `pitch` and `positions` on `pattern_ports` and `stretch_to_ports`: copies at a whole multiple of the wire pitch, or at given coordinates (D107).
- Changed: lint rule `port-pattern` no longer refuses named ports on a pattern port's edge; it refuses two pattern ports on one edge. `stretch_to_ports` on such an edge returns offsets for every port of the edge, and `pattern_ports` raises for a copy less than a wire pitch from a named port (D108).
- Added: `table(row, n, axis, head=None, *, grid=None, gaps=None, positions=None, head_align=None)`: `row` may be a sequence of unlike rows; `gaps`, `positions` and `head_align` are new (D109).
- Added: `fitted_table(..., fit="cross")`; `fit="step"` fits the step along the stepping axis (D109).
- Changed: lint rule `port-pattern` ignores the single-port node that the bundle writes for a lone pattern port; `symdef check` no longer fails on the reloaded bundle (D110).

## 0.23.0

- Added: `pattern_ports(symbol, edge, n, *, grid=DEFAULT_GRID)`, the symbol with the pattern port of `edge` expanded into `n` ports (1 to `MAX_REPEAT`) on the wire pitch, ids `k.<id>`, each with its bound lead and `marking.k.<id>` slot; it raises `InvalidValueError` naming the symbol, the edge and `n` (D104).
- Added: `Port.pattern` (TOML `pattern = true`, bundle key only when true) and lint rule `port-pattern` (ERROR, Ports): a pattern port shares its edge, has no cut on the edge's axis, or is in a node or path; 37 rules. `port-isolated` skips a pattern port (D104).
- Changed: `stretch_to_ports` on an edge with a pattern port takes any `n` up to `MAX_REPEAT`; every other edge is unchanged (D104).

## 0.22.0

- Changed: `keepout_box` is the body united with the bound leads (`Line`s with a `port`); a slot is a text slot and no longer enlarges it. A caller that read the keep-out as the room of the labels reads `slot_box`; `Measure.keepout` still holds the slots. The resolved JSON `keepout_box` moves with it (D101).
- Added: `only_ports(symbol, ports)`, the symbol with only the listed ports, their leads and `marking.<port>` slots; an unknown id raises `UnknownNameError` naming it and the symbol (D102).
- Added: `stretch_to_ports(symbol, axis, edge, n, *, grid=DEFAULT_GRID)`, the `(length, offsets)` that `stretch` takes so that `edge` carries `n` ports on the wire pitch; it raises `InvalidValueError` for a symbol with no cut on the axis, an edge across the axis, or `n` above the ports the edge declares (D102).

## 0.21.0

- Added: `text_tag(content, point, height_mm, *, anchor, font_family, turn=False, weight=Weight.NORMAL, tint=None, muted=None)`, one `<text>` in mm at a baseline point, and `corner_text(box, corner, height, font)`, the baseline point, anchor and `turned` that a box corner gives a text, as a `TextPlacement` (D100).
- Added: keyword-only `lanes` (default 1) and `pitch` (default `library.grid.wire_pitch`, in M) on `wire`. For `lanes` above 1 the symbol holds one polyline per lane, lane 0 on the points and lane k moved k * pitch towards +y on a horizontal run and +x on a vertical run, mitred at corners. `lanes=1` is unchanged; `lanes` below 1, `pitch` of 0 or less, and a closed wire with several lanes raise `InvalidValueError` (D99).
- Added: the symbol keys `body` and `keepout`, `[x0, y0, x1, y1]` in M; `Symbol.body` and `Symbol.keepout` (default None). `body_box` and `keepout_box` return a declared box exactly; `orient`, `translate`, `stretch`, `repeat` and `table` carry it (D98).
- Added: lint rule `element-outside-body` (ERROR, Geometry): a shape that leaves a declared body; 36 rules. `text-outside-body` measures against a declared body (D98).
- Added: the JSON schema's `body` and `keepout`; the resolved form writes them only when set.

## 0.20.0

- Added: `[grid] stretch_split = "weight" | "whole"` (default "weight") and `Grid.stretch_split`; the bundle writes it only when "whole" (D97).
- Added: a keyword-only `grid` on `stretch` and `table`; under "whole" a growth over several cuts splits in whole divisions, each cut but the last flooring its weighted share, and a growth that is not a whole number of divisions raises (D97). `fitted_table` and `fitted_symbol` pass `library.grid`.

## 0.19.0

- Changed: under `text_block = "grid"` a centred text sits at the slot box's start edge plus floor(length / 2) whole divisions, not at the true centre; "cap" is unchanged (D96).

## 0.18.0

- Added: `slot_lines(slot, text, height, font)`, one `TextPlacement` per `\n` line of a slot text, `LINE_PITCH` cap heights apart; `text_box`, `to_fragment` and `to_fragment_mm` draw and measure the whole block (D95).
- Added: `fitted_symbol(symbol, texts, library, text_height)`, a symbol stretched on each axis so every slot in `texts` holds its text (D95).
- Added: `wire(..., closed=False)`, keyword-only; `closed=True` draws a closed polyline (D95).
- Added: `[font] text_block = "cap" | "grid"` (default "cap"), `FontMetrics.text_block`, and a `grid` keyword on `slot_text`, `slot_lines`, `text_box` and `slot_box`; "grid" sets rows a whole number of divisions apart with the baseline an ascent below the block top (D95).
- Changed: a slot text containing `\n` is drawn as several rows; a string without one is unchanged.

## 0.17.0

- Added: `fitted_table(row, axis, texts, library, text_height, *, head=None, head_texts=None)`, a `table` whose columns are as wide as the widest text set in them, measured with `library.font` and rounded up to whole grid divisions (D94).

## 0.16.0

- Added: `[font]` with `files` takes `heights`, the capital heights in mm by name; `FontMetrics.heights` carries them (D93). `family` beside `files` stays refused.
- Added: `LibraryConfig.font_heights`, the `heights` of the files form, beside `font_files` and `font_name`; `font` stays None until the files are read (D93).
- Changed: the load error for a literal key beside `files` names the key and the fix.

## 0.15.0

- Added: `FontMetrics.family`, the family name a renderer resolves the font by. `measure_font` reads it from the regular face's typographic family (name ID 16), else its family (ID 1); `FontMetrics.name` stays ID 1. The literal `[font]` form takes an optional `family`, default `name`; `family` beside `files` is a load error, since the file gives it. The bundle's `font` object carries `family` (D92).

## 0.14.0

- Added: `measure(..., attach={slot_id: Symbol})`. The attached symbol's keep-out box is placed at the turned slot's point and side, as a slot's reserved box is (never rotated), and united with that slot's box; it is in `Measure.slots[slot_id]` and `Measure.keepout`. A key that is not a slot id raises `UnknownNameError`. Without `attach` the result is unchanged (D91).

## 0.13.0

- Added: `measure_font(regular, bold)` returning `FontMetrics`: it measures a regular and a bold TTF, given as bytes, into one advance table per `Weight`, the cap height, ascent and descent. `fonttools` is now a runtime dependency (D87).
- Added: `[font]` in `library.toml` may give `name` and `files` (`regular`, `bold`) instead of the metrics; `symdef build` measures the files, relative to `library.toml`, into the bundle. The literal form is unchanged (D87).
- Added: `Library.with_settings(module_mm=None, font=None, heights=None, lines=None)`, a validated replace. `font` is the two TTFs as bytes; `Grid` and `FontMetrics` run their own checks, then the check `text-outside-body` runs over every symbol and a hit raises `InvalidValueError` (D88, D90).
- Added: the check `text-outside-body` (D90), which measures a fixed text inside its symbol's body with the library font and is run by `load_library` (with the library's font, raising `LibraryError`) and by `Library.with_settings` in place of `text-too-large`.
- Added: `[lines]` in `library.toml` (`normal`, `thick`: millimetres) and `Library.lines`, a read-only map from `Weight` to millimetres; the bundle carries it when not empty. A wire weight with no width is a load error (D89).

## 0.12.0

- Removed from `symdef`, now on `symdef.authoring`: `build`, `check`, `init`, `lint`, `write_build`, `stale_build`, `RULES`, `finding_key`, `LibraryConfig` (D84).
- Added: `SymdefError`, the base of every error symdef raises, with `InvalidValueError`, `UnknownNameError`, `UnknownSymbolError` and `LibraryError` under it. None subclasses `ValueError`, `KeyError` or `OSError`, so an `except` on a builtin no longer catches them (D80).
- Renamed: `GraphicalSymbolsError` is now `SymdefError`; the old name is removed, with no alias (D80).
- Added: `GridPoint`, `GridBox` (with `GridBox.union`) and `GridPort`, whose coordinates are whole grid divisions (D81).
- Added: `measure(symbol, orientation, library, texts=None, text_height=None)` returning `Measure`: body, keepout, slots and ports in whole divisions, already turned (D82).
- Changed: `FontMetrics.advances` is one table per `Weight` (`[font.advances.normal]` and `[font.advances.thick]` in `library.toml`); `thick_factor` is removed, and the bundle's `font.advances` has a `normal` and a `thick` table (D82).
- Added: `to_placed_fragment(symbol, orientation, at, library, ...)`, a fragment inside one `translate` read from a `GridPoint` (D83).
- Added: `Grid.wire_pitch` (8) and `Grid.wire_pitch_fine` (4), in divisions, and `[grid]` keys of the same names; the loader refuses a third pitch, a fine pitch that does not divide the standard one, and a port off the standard pitch (D86).
- Added: `FontMetrics.heights`, a read-only map of names to capital heights in millimetres, from `[font.heights]` (D86).
- Deprecated: `to_fragment_mm` is listed for removal in 0.13, once its callers use `to_placed_fragment`.

## 0.11.0

- Added: `Library.font` and `Library.grid`, read from `[font]` and `[grid]` in `library.toml` and carried by the bundle; `FontMetrics`, `Grid`, `text_width`.
- Added: `slot_text`, `TextPlacement`, `to_divisions`, `from_divisions`, `ceil_divisions`, `Box.union`, `slots_box`.
- Widened: `body_box`, `keepout_box` and `slot_box` take `font=None` (`slot_box` also `text` and `height`), and `lint` takes `grid`; with none, output is as before.
- Made public: `orient_box`, `orient_point`, `orient_direction`, `pole_pitch`, `pole_port`, `nodes_of`.
- Changed: `load_library` and `load_bundle` return a `Library` whose `symbols` is read-only (D73 to D78).

## 0.10.0

- Widened: `Slot.side` is `Direction | Centre`; the centred side `C` puts the box and the text on `at` (retroactive; the type widened in this release, D67 to D71).
- Added: several `[[stretch]]` cuts per axis, each with a `weight`; a line or polyline may say `between = true`.
