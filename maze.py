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
        if isinstance(self.width, bool) or not isinstance(self.width, int):
            raise TypeError("width must be an integer")
        if isinstance(self.height, bool) or not isinstance(self.height, int):
            raise TypeError("height must be an integer")
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

    def reserve_pattern_cells(self, cells: set[Coordinate]) -> None:
        """Reserve fully closed cells for the mandatory pattern."""
        candidate = set(cells)
        for position in candidate:
            if not isinstance(position, Coordinate):
                raise TypeError("pattern cells must be Coordinate instances")
            if not self.in_bounds(position):
                raise ValueError(
                    f"pattern cell out of bounds: ({position.x}, {position.y})"
                )
            if self.get_walls(position) != ALL_WALLS:
                raise ValueError(
                    f"pattern cell must be fully closed: "
                    f"({position.x}, {position.y})"
                )
        self.pattern_cells = candidate
