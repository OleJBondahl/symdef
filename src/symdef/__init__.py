"""Standard-agnostic core for graphical symbols."""

from symdef._version import LIBRARY_VERSION
from symdef.boxes import body_box, keepout_box, slot_box
from symdef.errors import GraphicalSymbolsError, LibraryError, UnknownSymbolError
from symdef.files import load_bundle, load_library, stale_build, write_build
from symdef.geometry import (
    Arc,
    Box,
    Circle,
    Direction,
    Element,
    Fill,
    Line,
    Orientation,
    Point,
    Polyline,
    Style,
    Text,
    Weight,
)
from symdef.lint import RULES, finding_key, lint
from symdef.model import (
    Allow,
    Anchor,
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
)
from symdef.orient import orient, translate
from symdef.project import build, check, init
from symdef.repeat import repeat
from symdef.stretch import stretch
from symdef.svg import to_fragment, to_svg
from symdef.svg_mm import to_fragment_mm
from symdef.units import DEFAULT_MODULE_MM, GRID_DIVISION, on_grid, snap

__all__ = [
    "DEFAULT_MODULE_MM",
    "GRID_DIVISION",
    "LIBRARY_VERSION",
    "RULES",
    "Allow",
    "Anchor",
    "Arc",
    "Box",
    "Circle",
    "Direction",
    "Element",
    "Fill",
    "Finding",
    "GraphicalSymbolsError",
    "Library",
    "LibraryConfig",
    "LibraryError",
    "Line",
    "Node",
    "Orientation",
    "Path",
    "Point",
    "Polyline",
    "Port",
    "Reference",
    "Severity",
    "Slot",
    "Status",
    "Stretch",
    "Style",
    "Symbol",
    "SymbolKind",
    "Text",
    "UnknownSymbolError",
    "Vocabulary",
    "Weight",
    "body_box",
    "build",
    "check",
    "finding_key",
    "init",
    "keepout_box",
    "lint",
    "load_bundle",
    "load_library",
    "on_grid",
    "orient",
    "repeat",
    "slot_box",
    "snap",
    "stale_build",
    "stretch",
    "to_fragment",
    "to_fragment_mm",
    "to_svg",
    "translate",
    "write_build",
]
