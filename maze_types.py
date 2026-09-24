"""Shared value types for the maze model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Coordinate:
    """Represent an integer maze coordinate."""

    x: int
    y: int

    def __post_init__(self) -> None:
        if isinstance(self.x, bool) or not isinstance(self.x, int):
            raise TypeError("x must be an integer")
        if isinstance(self.y, bool) or not isinstance(self.y, int):
            raise TypeError("y must be an integer")

    def as_tuple(self) -> tuple[int, int]:
        """Return the coordinate as an (x, y) tuple."""
        return self.x, self.y
