"""Generate perfect mazes and reserve the visible 42 pattern."""
from maze_types import Coordinate

_PATTERN_MASK = (
    "1000111",
    "1000001",
    "1110111",
    "0010100",
    "0010111"
)


class MazeGenerator:
    """Prepare validated parameters for maze generation."""

    def __init__(
        self,
        width: int,
        height: int,
        seed: int | None = None,
    ) -> None:
        if isinstance(width, bool) or not isinstance(width, int):
            raise TypeError("width must be an integer")
        if isinstance(height, bool) or not isinstance(height, int):
            raise TypeError("height must be an integer")
        if width <= 0 or height <= 0:
            raise ValueError(
                "width and height must be greater than 0"
            )
        if seed is not None and (
            isinstance(seed, bool) or not isinstance(seed, int)
        ):
            raise TypeError("seed must be an integer or None")

        self.width = width
        self.height = height
        self.seed = seed

    def _mask_cells(self, origin: Coordinate) -> set[Coordinate]:
        """Return the reserved cells for the mask at the given origin."""
        return {
            Coordinate(origin.x + column, origin.y + row)
            for row, mask_row in enumerate(_PATTERN_MASK)
            for column, value in enumerate(mask_row)
            if value == "1"
        }
