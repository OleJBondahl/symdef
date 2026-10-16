"""Grid-division geometry: points, boxes and ports whose coordinates are whole divisions."""

from dataclasses import dataclass

from symdef.errors import InvalidValueError
from symdef.geometry import Direction


def _check_whole(owner: str, field: str, value: object) -> None:
    """Raise unless `value` is an int that is not a bool."""
    if isinstance(value, int) and not isinstance(value, bool):
        return
    msg = (
        f"{owner}.{field} is {value!r}; grid divisions are whole numbers; "
        "round with ceil_divisions or to_divisions"
    )
    raise InvalidValueError(msg)


@dataclass(frozen=True, slots=True)
class GridPoint:
    """A position in whole grid divisions."""

    x: int
    y: int

    def __post_init__(self) -> None:
        """Reject a coordinate that is not a whole number."""
        _check_whole("GridPoint", "x", self.x)
        _check_whole("GridPoint", "y", self.y)


@dataclass(frozen=True, slots=True)
class GridBox:
    """An axis-aligned rectangle in whole grid divisions, from its min corner to its max corner."""

    min: GridPoint
    max: GridPoint

    @property
    def width(self) -> int:
        """Horizontal extent in divisions."""
        return self.max.x - self.min.x

    @property
    def height(self) -> int:
        """Vertical extent in divisions."""
        return self.max.y - self.min.y

    @staticmethod
    def union(*boxes: GridBox) -> GridBox:
        """Return the smallest box holding all `boxes`; one box gives itself, none raises."""
        if not boxes:
            msg = "union needs at least one box"
            raise InvalidValueError(msg)
        return GridBox(
            GridPoint(min(b.min.x for b in boxes), min(b.min.y for b in boxes)),
            GridPoint(max(b.max.x for b in boxes), max(b.max.y for b in boxes)),
        )


@dataclass(frozen=True, slots=True)
class GridPort:
    """A connection point in whole grid divisions, with the direction it leaves the symbol."""

    id: str
    x: int
    y: int
    direction: Direction

    def __post_init__(self) -> None:
        """Reject a coordinate that is not a whole number."""
        _check_whole("GridPort", "x", self.x)
        _check_whole("GridPort", "y", self.y)
