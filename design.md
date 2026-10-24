# symdef: design

symdef is a standard-agnostic Python toolkit for graphical-symbol data, compatible with IEC.
Symbols are plain TOML files. The toolkit reads them, resolves composition, lints the wiring
contract, renders SVG and builds a resolved JSON bundle. It holds no symbols of its own for
any standard: data packages hold only data and reuse the toolkit and its gates. The design
stance is a pure core (no I/O, clock or global state outside a short listed set), frozen
data, one runtime dependency, and a strict rule set where every lint rule and gate is proven
able to fail by a deliberately broken fixture.

This page holds no design of its own. Each part has one home:

- Design: the symbol interface spec, `src/symdef/docs/SYMBOL_INTERFACE.html`. It ships as
  package data and is the only design document. It defines extents, overlap, orientations,
  the wire lane, placement, `repeat`, `stretch`, `table`, `wire`, the JSON output format and
  the public names.
- Rule set: the lint rules are in the same spec (`symdef.authoring.RULES` lists them). The
  purity gate is `scripts/fp_purity_gate.py`; the project rules (pins, dependencies, coverage,
  gates) are in `CLAUDE.md`, and `just ci` enforces them.
- Decision log: `docs/DECISIONS.md`, one entry per decision where the spec is silent.
- Changelog: `docs/CHANGELOG.md`, per release.
- Using it: `docs/GUIDE.md` and `docs/TUTORIAL.md`, published at
  <https://olejbondahl.github.io/symdef/>.

Review: a change to the spec or to a rule goes through proper review before it lands. It
carries a dated entry in the spec's change list and in `docs/DECISIONS.md`, and a new or
changed rule or gate carries a failing fixture. A reviewer other than its author checks it against the spec and the rule set, and the maintainer approves the merge.
