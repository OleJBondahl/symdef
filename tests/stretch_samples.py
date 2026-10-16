"""Builders and golden cases of the 0.9.0 byte-identity guard. Plain functions, no pytest.

The tutorial set has no stretch symbols, so `card` and `slab` are synthetic. The golden files of
`golden_files()` are written by `claude-tools/gen_stretch_goldens.py` and read by the test.
"""

from pathlib import Path
from typing import Any

import symdef
from symdef import Weight
from symdef.boxes import body_box
from symdef.geometry import Circle, Direction, Line, Point, Polyline, Text
from symdef.model import Anchor, Port, Reference, Slot, Status, Stretch, Symbol, SymbolKind
from symdef.serialize import bundle_to_data, symbol_to_data, to_json
from symdef.stretch import stretch
from symdef.table import table

N, E, S, W = Direction.N, Direction.E, Direction.S, Direction.W
ROOT = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).parent / "fixtures" / "stretch_0_9"
LIBRARY = symdef.load_library(ROOT / "docs" / "tutorial-set")
NUMBERS = sorted(LIBRARY.symbols)
# The tutorial symbols of kind "symbol"; `table` accepts each of them for n = 1 and n = 4.
TABLE_NUMBERS = ("S00016", "S00227", "S00230", "S00254", "S00305", "S90001", "S90002", "S90003")
MM: dict[str, Any] = {
    "module_mm": 2.5,
    "weights_mm": {Weight.NORMAL: 0.25, Weight.THICK: 0.5},
    "dash_mm": (1.2, 0.6),
    "dash_dot_mm": (3.0, 0.6, 0.6, 0.6),
    "font_family": "Inter, sans-serif",
    "font_mm": 2.0,
    "cap_ratio": 0.7,
}
PORT_X = {"1": 4, "2": 12, "3": 20, "4": 28}


def card() -> Symbol:
    """A PLC card: a 32 wide body, cut at x = 16, four channels on the S edge."""
    return Symbol(
        name="card",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "1"),
        elements=(
            Polyline((Point(0, 0), Point(32, 0), Point(32, 8), Point(0, 8)), closed=True),
            *(Line(Point(x, 8), Point(x, 10), port=pid) for pid, x in PORT_X.items()),
        ),
        ports=tuple(Port(pid, Point(x, 10), S) for pid, x in PORT_X.items()),
        slots=(
            Slot("tag", Point(2, 2), E, (4, 1)),
            *(Slot(f"marking.{pid}", Point(x, 12), S, (3, 1)) for pid, x in PORT_X.items()),
        ),
        stretch=(Stretch("x", 16),),
    )


def slab() -> Symbol:
    """A 16 by 12 body cut at x = 8 and y = 6; every slot lies wholly on one side of both cuts."""
    return Symbol(
        name="slab",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference("X", "2"),
        elements=(
            Polyline((Point(0, 0), Point(16, 0), Point(16, 12), Point(0, 12)), closed=True),
            Line(Point(4, 3), Point(12, 3)),  # crosses x = 8
            Line(Point(3, 2), Point(3, 10)),  # crosses y = 6
            Circle(Point(12, 9), 1.5),  # wholly beyond x = 8 and y = 6
            Text("A", Point(2, 9)),  # wholly before x = 8, beyond y = 6
            Line(Point(16, 3), Point(18, 3), port="E1"),
            Line(Point(4, 12), Point(4, 14), port="S1"),
        ),
        ports=(Port("E1", Point(16, 3), E), Port("S1", Point(4, 12), S)),
        anchors=(Anchor("a", Point(0, 4), W),),
        slots=(
            Slot("tag", Point(1, 1), E, (2, 1)),
            Slot("marking.W1", Point(0, 9), W, (2, 1)),
            Slot("marking.S1", Point(4, 12), S, (1, 2), turn=True),
            Slot("note", Point(12, 0), N, (2, 1)),
            Slot("marking.E1", Point(16, 3), E, (2, 1)),
        ),
        stretch=(Stretch("x", 8), Stretch("y", 6)),
    )


SAMPLES = {"card": card(), "slab": slab()}


def _json(symbol: Symbol) -> bytes:
    """Return a symbol's canonical JSON bytes."""
    return to_json(symbol_to_data(symbol)).encode()


def golden_files() -> dict[str, bytes]:
    """Return every golden file of the set, by file name."""
    files = {"tutorial.bundle.json": to_json(bundle_to_data(LIBRARY)).encode()}
    for number in NUMBERS:
        files[f"tutorial.{number}.json"] = _json(LIBRARY.get(number))
    for name, sample in SAMPLES.items():
        files[f"{name}.json"] = _json(sample)
        for cut in sample.stretch:
            body = body_box(sample)
            natural = body.width if cut.axis == "x" else body.height
            for label, length in (
                ("natural", natural),
                ("plus4", natural + 4),
                ("plus9", natural + 9),
            ):
                grown = stretch(sample, cut.axis, length)
                stem = f"{name}.{cut.axis}.{label}"
                files[f"{stem}.json"] = _json(grown)
                files[f"{stem}.svg"] = symdef.to_fragment(grown).encode()
                files[f"{stem}.mm.svg"] = symdef.to_fragment_mm(grown, **MM).encode()
    for number in TABLE_NUMBERS:
        row = LIBRARY.get(number)
        for n, axis in ((1, "x"), (4, "x"), (4, "y")):
            tabled = table(row, n, axis)
            stem = f"table.{number}.{n}{axis}"
            files[f"{stem}.json"] = _json(tabled)
            files[f"{stem}.svg"] = symdef.to_fragment(tabled).encode()
    return files
