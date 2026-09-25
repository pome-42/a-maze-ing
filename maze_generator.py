"""Generate perfect mazes and reserve the visible 42 pattern."""
from dataclasses import dataclass

from maze import DIRECTION_STEPS, Maze
from maze_types import Coordinate, Wall

_PATTERN_MASK = (
    "1000111",
    "1000001",
    "1110111",
    "0010100",
    "0010111"
)


@dataclass(frozen=True)
class GeneratedMaze:
    """Store a generated maze and its generation metadata."""

    maze: Maze
    entry: Coordinate
    exit: Coordinate
    seed: int | None

    @property
    def grid(self) -> tuple[tuple[Wall, ...], ...]:
        """Return the generated grid snapshot."""
        return self.maze.grid

    @property
    def pattern_cells(self) -> frozenset[Coordinate]:
        """Return the reserved 42 cells."""
        return self.maze.pattern_cells


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

    def _mask_fits(self, origin: Coordinate) -> bool:
        """Return whether the complete mask fits inside the maze."""
        return all(
            0 <= cell.x < self.width and 0 <= cell.y < self.height
            for cell in self._mask_cells(origin)
        )

    def _candidate_origins(self) -> list[Coordinate]:
        """Return mask origins that keep every pattern cell in bounds."""
        origins: list[Coordinate] = []

        for y in range(self.height):
            for x in range(self.width):
                origin = Coordinate(x, y)
                if self._mask_fits(origin):
                    origins.append(origin)

        return origins

    def _candidate_origins_without_terminals(
        self,
        entry: Coordinate,
        exit: Coordinate,
    ) -> list[Coordinate]:
        """Return fitting origins that do not reserve entry or exit."""
        origins: list[Coordinate] = []

        for origin in self._candidate_origins():
            pattern_cells = self._mask_cells(origin)
            if entry in pattern_cells or exit in pattern_cells:
                continue
            origins.append(origin)

        return origins

    def _is_connected_without_pattern(
        self,
        pattern_cells: set[Coordinate],
        start: Coordinate,
    ) -> bool:
        """Return whether all non-pattern cells form one component."""
        playable = {
            Coordinate(x, y)
            for y in range(self.height)
            for x in range(self.width)
        } - pattern_cells

        if start not in playable:
            return False

        visited = {start}
        pending = [start]

        while pending:
            current = pending.pop()

            for direction, (dx, dy) in DIRECTION_STEPS.items():
                neighbour = Coordinate(
                    current.x + dx,
                    current.y + dy,
                )
                if (
                    neighbour in playable
                    and neighbour not in visited
                ):
                    visited.add(neighbour)
                    pending.append(neighbour)

        return visited == playable

    def _select_pattern_cells(
        self,
        entry: Coordinate,
        exit: Coordinate,
    ) -> set[Coordinate] | None:
        """Select a connected pattern placement avoiding terminals."""
        fitting_origins = self._candidate_origins()

        if not fitting_origins:
            return None

        terminal_safe_origins = (
            self._candidate_origins_without_terminals(
                entry,
                exit,
            )
        )

        if not terminal_safe_origins:
            raise ValueError(
                "no pattern placement avoids the entry and exit"
            )

        for origin in terminal_safe_origins:
            pattern_cells = self._mask_cells(origin)

            if self._is_connected_without_pattern(
                pattern_cells,
                entry,
            ):
                return pattern_cells

        raise ValueError(
            "no pattern placement preserves playable-cell connectivity"
        )

    def _reserve_pattern(
        self,
        maze: Maze,
        entry: Coordinate,
        exit: Coordinate,
    ) -> set[Coordinate]:
        """Reserve the selected 42 cells in the maze."""
        pattern_cells = self._select_pattern_cells(entry, exit)

        if pattern_cells is None:
            return set()

        maze.reserve_pattern_cells(pattern_cells)
        return pattern_cells

    def _validate_terminals(
        self,
        entry: Coordinate,
        exit: Coordinate,
    ) -> None:
        """Validate entry and exit coordinates for generation."""
        if not isinstance(entry, Coordinate):
            raise TypeError("entry must be a Coordinate")
        if not isinstance(exit, Coordinate):
            raise TypeError("exit must be a Coordinate")
        if not self._in_bounds(entry):
            raise ValueError("entry must be inside the maze bounds")
        if not self._in_bounds(exit):
            raise ValueError("exit must be inside the maze bounds")
        if entry == exit:
            raise ValueError("entry and exit must be different")

    def _in_bounds(self, position: Coordinate) -> bool:
        """Return whether a coordinate is inside the maze."""
        return (
            0 <= position.x < self.width
            and 0 <= position.y < self.height
        )

    def _playable_cells(
        self,
        pattern_cells: set[Coordinate],
    ) -> set[Coordinate]:
        """Return every cell that can be used as a passage."""
        all_cells = {
            Coordinate(x, y)
            for y in range(self.height)
            for x in range(self.width)
        }
        return all_cells - pattern_cells

    def _neighbours(
        self,
        position: Coordinate,
    ) -> list[tuple[Coordinate, Wall]]:
        """Return in-bounds neighbours in fixed direction order."""
        neighbours: list[tuple[Coordinate, Wall]] = []

        for direction, (dx, dy) in DIRECTION_STEPS.items():
            neighbour = Coordinate(
                position.x + dx,
                position.y + dy,
            )
            if self._in_bounds(neighbour):
                neighbours.append((neighbour, direction))

        return neighbours
