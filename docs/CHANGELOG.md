# Changelog

What changed in the public surface of each release: a name added, removed or moved, and a type that widened. Every change to `surface.toml` has a line here. The reasons are in [the decisions](DECISIONS.md).

## 0.13.0

- Added: `measure_font(regular, bold)` returning `FontMetrics`: it measures a regular and a bold TTF, given as bytes, into one advance table per `Weight`, the cap height, ascent and descent. `fonttools` is now a runtime dependency (D87).
- Added: `[font]` in `library.toml` may give `name` and `files` (`regular`, `bold`) instead of the metrics; `symdef build` measures the files, relative to `library.toml`, into the bundle. The literal form is unchanged (D87).
- Added: `Library.with_settings(module_mm=None, font=None, heights=None, lines=None)`, a validated replace. `font` is the two TTFs as bytes; `Grid` and `FontMetrics` run their own checks, then the check `text-outside-body` runs over every symbol and a hit raises `InvalidValueError` (D88, D90).
- Added: the check `text-outside-body` (D90), which measures a fixed text inside its symbol's body with the library font and is run by `Library.with_settings` in place of `text-too-large`.
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
