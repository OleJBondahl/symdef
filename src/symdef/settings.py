"""`Library.with_settings`: a validated replace of grid, font, heights, lines, dashes (D88)."""

import math
from collections.abc import Mapping, Sequence
from dataclasses import replace

from symdef.dash import dash_problems, pattern_problem
from symdef.errors import InvalidValueError
from symdef.font import FontMetrics
from symdef.fontmeasure import measure_font
from symdef.geometry import Weight
from symdef.lines import lines_problems
from symdef.lint.textbody import text_outside_body
from symdef.model import Library

_PAIR = 2


def _positive(name: str, value: object) -> float:
    """Return `value` if it is a finite number above zero, else raise naming `name`."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        msg = f"{name} {value!r} is not a number; give millimetres above zero"
        raise InvalidValueError(msg)
    if value <= 0:
        msg = f"{name} {value!r} is not above zero; give millimetres above zero"
        raise InvalidValueError(msg)
    return value


def _is_font_pair(font: object) -> bool:
    """Return whether `font` is a pair of bytes."""
    return (
        isinstance(font, tuple) and len(font) == _PAIR and all(isinstance(f, bytes) for f in font)
    )


def _font(library: Library, font: object, heights: object) -> FontMetrics:
    """Return the library's font with the measured `font` and the given `heights` applied."""
    metrics = library.font
    if font is not None:
        if not _is_font_pair(font):
            msg = f"font {type(font).__name__} is not a pair of bytes; give (regular_ttf, bold_ttf)"
            raise InvalidValueError(msg)
        metrics = replace(
            measure_font(*font),  # ty: ignore[not-iterable] - font is a checked pair
            heights=metrics.heights,
            text_block=metrics.text_block,
        )
    if heights is None:
        return metrics
    if not isinstance(heights, Mapping) or not all(isinstance(k, str) for k in heights):
        msg = "heights is not a mapping of names to millimetres; fix its shape"
        raise InvalidValueError(msg)
    return replace(metrics, heights={k: _positive(f"height {k!r}", v) for k, v in heights.items()})


def _lines(library: Library, lines: object) -> Mapping[Weight, float]:
    """Return the library's widths, or the checked `lines` that replace them."""
    if lines is None:
        return library.lines
    if not isinstance(lines, Mapping) or not all(isinstance(k, Weight) for k in lines):
        msg = "lines is not a mapping of Weight to millimetres; fix its shape"
        raise InvalidValueError(msg)
    widths = {k: _positive(f"line width {k.name.lower()!r}", v) for k, v in lines.items()}
    problems = lines_problems(library.wires, widths)
    if problems:
        raise InvalidValueError("; ".join(problems))
    return widths


def _dash(library: Library, dash: object) -> Mapping[str, tuple[float, ...]]:
    """Return the library's dash patterns, or the checked `dash` that replaces them."""
    if dash is None:
        return library.dash
    if not isinstance(dash, Mapping) or not all(isinstance(k, str) for k in dash):
        msg = "dash is not a mapping of names to lists of millimetres; fix its shape"
        raise InvalidValueError(msg)
    patterns = {}
    for name, pattern in dash.items():
        if not isinstance(pattern, Sequence) or isinstance(pattern, str):
            msg = f"dash {name!r} is not a list of millimetres; give an even count of lengths"
            raise InvalidValueError(msg)
        problem = pattern_problem(name, pattern)
        if problem:
            msg = f"dash {problem}"
            raise InvalidValueError(msg)
        patterns[name] = tuple(_positive(f"dash {name!r} length", n) for n in pattern)
    problems = dash_problems(library, library.wires, patterns)
    if problems:
        raise InvalidValueError("; ".join(problems))
    return patterns


def with_settings(  # noqa: PLR0913 - one keyword per replaceable setting
    library: Library,
    *,
    module_mm: float | None = None,
    font: tuple[bytes, bytes] | None = None,
    heights: Mapping[str, float] | None = None,
    lines: Mapping[Weight, float] | None = None,
    dash: Mapping[str, Sequence[float]] | None = None,
) -> Library:
    """Return `library` with the given grid module, font, text heights, lines and dashes replaced.

    `dash` is the whole `[dash]` table in millimetres; it replaces the library's.

    `font` is the bytes of a regular and a bold TTF, measured by `measure_font`. `Grid` and
    `FontMetrics` run their own checks; then `text_outside_body` runs over every symbol. An argument
    left as None keeps the library's value.

    Raises:
        InvalidValueError: If a value is unusable, a wire weight has no width, a dash pattern is
            malformed or missing for a style in use, a face is not a usable font, or a symbol's
            text leaves its body; the message names each hit.
    """
    grid = library.grid if module_mm is None else replace(library.grid, module_mm=module_mm)
    result = replace(
        library,
        grid=grid,
        font=_font(library, font, heights),
        lines=_lines(library, lines),
        dash=_dash(library, dash),
    )
    hits = [
        found.message
        for symbol in result
        for found in text_outside_body(symbol, result.font, result.grid.module_mm)
    ]
    if hits:
        raise InvalidValueError("text outside its body after the new settings: " + "; ".join(hits))
    return result
