from dataclasses import dataclass, field
from maze_types import Coordinate


NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8
ALL_WALLS = NORTH | EAST | SOUTH | WEST


@dataclass
class Maze:
    """Store the mutable grid and reserved cells of a maze."""

    width: int
    height: int
    grid: list[list[int]] = field(init=False)
    pattern_cells: set[Coordinate] = field(default_facotry=set)

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be greater than 0")
        if self.height <= 0:
            raise ValueError("height must be greater than 0")

        self.grid = [
            [ALL_WALLS for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def in_bounds(self, x: int, y: int) -> bool:
        """Return whether the coordinate is inside the maze."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_walls(self, x: int, y: int) -> int:
        """Return the wall bitmask at the given coordinate."""
        if not self.in_bounds(x, y):
            raise IndexError(f"coordinate out of bounds: ({x}, {y})")
        return self.grid[y][x]
