"""A sheet as one SVG document: the page wrapper and a bold layer (D122)."""

from symdef.svg import _num


def bold_layer(fragment: str) -> str:
    """Return `fragment` inside one group whose text is drawn bold."""
    return f'<g font-weight="bold">{fragment}</g>'


def sheet_svg(width_mm: float, height_mm: float, body: str, *, margin_mm: float) -> str:
    """Return one sheet's SVG: `body`, drawn in mm, on a page `width_mm` by `height_mm`.

    A margin `m` widens the page by `m` on every side: the viewBox starts at `-m -m` and the
    width and height grow by `2m`. A margin of 0 gives the plain page. The numbers are written
    as the shapes write theirs (at most four decimals, a whole number without `.0`, D141);
    `margin_mm` is required, symdef holds no margin default.
    """
    if not margin_mm:
        w, h = _num(width_mm), _num(height_mm)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
            f'viewBox="0 0 {w} {h}">{body}</svg>'
        )
    wide, high = _num(width_mm + 2 * margin_mm), _num(height_mm + 2 * margin_mm)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{wide}mm" height="{high}mm" '
        f'viewBox="{_num(-margin_mm)} {_num(-margin_mm)} {wide} {high}">{body}</svg>'
    )
