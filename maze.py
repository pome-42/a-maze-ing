from dataclasses import dataclass, field

from maze_types import ALL_WALLS, Coordinate, Wall


@dataclass
class Maze:
    """Store the mutable grid and reserved cells of a maze."""

    width: int
    height: int
    grid: list[list[Wall]] = field(init=False)
    pattern_cells: set[Coordinate] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be greater than 0")
        if self.height <= 0:
            raise ValueError("height must be greater than 0")

        self.grid = [
            [ALL_WALLS for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def in_bounds(self, position: Coordinate) -> bool:
        """Return whether the coordinate is inside the maze."""
        return (
            0 <= position.x < self.width
            and 0 <= position.y < self.height
        )

    def get_walls(self, position: Coordinate) -> Wall:
        """Return the wall bitmask at the given coordinate."""
        if not self.in_bounds(position):
            raise IndexError(
                f"coordinate out of bounds: ({position.x}, {position.y})"
            )
        return self.grid[position.y][position.x]
