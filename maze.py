from dataclasses import dataclass, field

from maze_types import ALL_WALLS, Coordinate, Wall


DIRECTION_STEPS = {
    Wall.NORTH: (0, -1),
    Wall.EAST: (1, 0),
    Wall.SOUTH: (0, 1),
    Wall.WEST: (-1, 0)
}

OPPOSITE_WALLS = {
    Wall.NORTH: Wall.SOUTH,
    Wall.EAST: Wall.WEST,
    Wall.SOUTH: Wall.NORTH,
    Wall.WEST: Wall.EAST
}


@dataclass
class Maze:
    """Store the mutable grid and reserved cells of a maze."""

    width: int
    height: int
    grid: list[list[Wall]] = field(init=False)
    _pattern_cells: set[Coordinate] = field(
        init=False,
        default_factory=set,
    )

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

    def open_wall(self, position: Coordinate, direction: Wall) -> None:
        """Open one wall and the matching wall of its neighbour."""
        if not isinstance(position, Coordinate):
            raise TypeError("position must be a Coordinate")
        if not self.in_bounds(position):
            raise IndexError(
                f"coordinate out of bounds: ({position.x}, {position.y})"
            )
        if not isinstance(direction, Wall) or direction not in DIRECTION_STEPS:
            raise ValueError("direction must be one cardinal Wall value")
        if position in self._pattern_cells:
            raise ValueError("cannot open a wall of a pattern cell")

        dx, dy = DIRECTION_STEPS[direction]
        neighbour = Coordinate(position.x + dx, position.y + dy)
        if not self.in_bounds(neighbour):
            raise ValueError("cannot open a wall on the outer boundary")
        if neighbour in self._pattern_cells:
            raise ValueError("cannot open a wall towards a pattern cell")

        opposite = OPPOSITE_WALLS[direction]
        self.grid[position.y][position.x] &= ~direction
        self.grid[neighbour.y][neighbour.x] &= ~opposite

    @property
    def pattern_cells(self) -> frozenset[Coordinate]:
        """Return the reserved pattern cells without exposing mutable state."""
        return frozenset(self._pattern_cells)

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
        self._pattern_cells = candidate
