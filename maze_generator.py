"""Generate perfect mazes and reserve the visible 42 pattern."""
from dataclasses import dataclass
import random
import secrets

from maze import DIRECTION_STEPS, OPPOSITE_WALLS, Maze
from maze_types import Coordinate, Wall
from maze_validator import (
    MazeValidationInput,
    ValidationReport,
    validate_maze,
)

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
    seed: int
    pattern_omitted: bool

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
        resolved_seed = (
            seed if seed is not None else secrets.randbits(64)
        )
        self.seed = resolved_seed
        self._random = random.Random(resolved_seed)

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

        center_x = (self.width - len(_PATTERN_MASK[0])) / 2
        center_y = (self.height - len(_PATTERN_MASK)) / 2
        origins.sort(
            key=lambda origin: (
                abs(origin.x - center_x) + abs(origin.y - center_y),
                origin.y,
                origin.x,
            )
        )
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

    def _carve_tree(
        self,
        maze: Maze,
        playable_cells: set[Coordinate],
        start: Coordinate,
    ) -> None:
        """Carve a spanning tree through every playable cell."""
        if start not in playable_cells:
            raise ValueError("start must be a playable cell")

        visited = {start}
        stack = [start]

        while stack:
            current = stack[-1]
            choices = [
                (neighbour, direction)
                for neighbour, direction in self._neighbours(current)
                if (
                    neighbour in playable_cells
                    and neighbour not in visited
                )
            ]

            if not choices:
                stack.pop()
                continue

            neighbour, direction = self._random.choice(choices)
            maze.open_wall(current, direction)
            visited.add(neighbour)
            stack.append(neighbour)

        if visited != playable_cells:
            raise ValueError(
                "playable cells cannot form one connected maze"
            )

    def generate(
        self,
        entry: Coordinate = Coordinate(0, 0),
        exit: Coordinate | None = None,
        perfect: bool = True,
    ) -> GeneratedMaze:
        """Generate a maze in the requested perfectness mode."""
        if not isinstance(perfect, bool):
            raise TypeError("perfect must be a bool")
        self._random = random.Random(self.seed)
        if not perfect:
            return self._generate_non_perfect(entry, exit)

        return self._generate_perfect(entry, exit)

    def _validation_report(
        self,
        result: GeneratedMaze,
        perfect: bool,
    ) -> ValidationReport:
        """Return an independent validation report for a result."""
        return validate_maze(
            MazeValidationInput(
                grid=result.grid,
                width=self.width,
                height=self.height,
                entry=result.entry,
                exit=result.exit,
                pattern_cells=result.pattern_cells,
                perfect=perfect,
            )
        )

    def _candidate_edges(
        self,
        maze: Maze,
        playable_cells: set[Coordinate],
    ) -> list[tuple[Coordinate, Wall]]:
        """Return closed, in-bounds edges between playable cells."""
        candidates: list[tuple[Coordinate, Wall]] = []
        for y in range(self.height):
            for x in range(self.width):
                current = Coordinate(x, y)
                if current not in playable_cells:
                    continue
                for direction in (Wall.EAST, Wall.SOUTH):
                    dx, dy = DIRECTION_STEPS[direction]
                    neighbour = Coordinate(x + dx, y + dy)
                    if neighbour not in playable_cells:
                        continue
                    if maze.get_walls(current) & direction:
                        candidates.append((current, direction))
        return candidates

    def _preview_non_perfect_opening(
        self,
        maze: Maze,
        entry: Coordinate,
        exit: Coordinate,
        direction: Wall,
        position: Coordinate,
    ) -> ValidationReport:
        """Return the validation report for a hypothetical opening."""
        grid = [list(row) for row in maze.grid]
        dx, dy = DIRECTION_STEPS[direction]
        neighbour = Coordinate(position.x + dx, position.y + dy)
        grid[position.y][position.x] &= ~direction
        grid[neighbour.y][neighbour.x] &= ~OPPOSITE_WALLS[direction]
        snapshot = GeneratedMaze(
            maze=maze,
            entry=entry,
            exit=exit,
            seed=self.seed,
            pattern_omitted=not maze.pattern_cells,
        )
        return validate_maze(
            MazeValidationInput(
                grid=tuple(tuple(row) for row in grid),
                width=self.width,
                height=self.height,
                entry=snapshot.entry,
                exit=snapshot.exit,
                pattern_cells=snapshot.pattern_cells,
                perfect=False,
            )
        )

    @staticmethod
    def _has_only_mode_errors(report: ValidationReport) -> bool:
        """Return whether a report contains no structural errors."""
        mode_prefixes = (
            "corner ",
            "no center cell",
            "non-perfect maze must",
        )
        return all(
            error.startswith(mode_prefixes)
            for error in report.errors
        )

    def _generate_non_perfect(
        self,
        entry: Coordinate,
        exit: Coordinate | None,
    ) -> GeneratedMaze:
        """Generate a connected maze with multiple independent routes."""
        result = self._generate_perfect(entry, exit)
        playable_cells = self._playable_cells(set(result.pattern_cells))
        while True:
            current_report = self._validation_report(
                result,
                perfect=False,
            )
            if (
                current_report.loop_count >= 2
                and current_report.dead_end_count <= 2
            ):
                break

            candidates = self._candidate_edges(
                result.maze,
                playable_cells,
            )
            self._random.shuffle(candidates)
            scored: list[tuple[int, int, int, int, Coordinate, Wall]] = []
            for position, direction in candidates:
                report = self._preview_non_perfect_opening(
                    result.maze,
                    result.entry,
                    result.exit,
                    direction,
                    position,
                )
                if self._has_only_mode_errors(report):
                    scored.append(
                        (
                            report.dead_end_count,
                            -report.loop_count,
                            position.y,
                            position.x,
                            position,
                            direction,
                        )
                    )

            if not scored:
                break

            _, _, _, _, position, direction = min(scored)
            result.maze.open_wall(position, direction)

        report = self._validation_report(result, perfect=False)
        if not report.is_valid:
            if not self._has_only_mode_errors(report):
                raise RuntimeError(
                    "generated maze failed validation: "
                    + "; ".join(report.errors)
                )
            raise ValueError(
                "cannot generate a non-perfect maze: "
                + "; ".join(report.errors)
            )
        return result

    def _generate_perfect(
        self,
        entry: Coordinate,
        exit: Coordinate | None,
    ) -> GeneratedMaze:
        """Generate a perfect maze and return its result."""
        if exit is None:
            exit = Coordinate(self.width - 1, self.height - 1)

        self._validate_terminals(entry, exit)

        maze = Maze(self.width, self.height)
        pattern_cells = self._reserve_pattern(
            maze,
            entry,
            exit,
        )
        playable_cells = self._playable_cells(pattern_cells)
        self._carve_tree(maze, playable_cells, entry)

        result = GeneratedMaze(
            maze=maze,
            entry=entry,
            exit=exit,
            seed=self.seed,
            pattern_omitted=not pattern_cells,
        )

        report = self._validation_report(result, perfect=True)

        if not report.is_valid:
            raise RuntimeError(
                "generated maze failed validation: "
                + "; ".join(report.errors)
            )

        return result
