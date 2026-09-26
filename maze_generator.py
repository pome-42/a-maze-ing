"""Generate perfect mazes and reserve the visible 42 pattern."""
from dataclasses import dataclass
from collections.abc import Callable
import heapq
import random
import secrets

from maze import DIRECTION_STEPS, Maze
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

GenerationStep = Callable[[tuple[tuple[Wall, ...], ...]], None]


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

    def _pattern_preserves_non_perfect_terminals(
        self,
        pattern_cells: set[Coordinate],
    ) -> bool:
        """Return whether corners and a center candidate remain playable."""
        corners = {
            Coordinate(0, 0),
            Coordinate(self.width - 1, 0),
            Coordinate(0, self.height - 1),
            Coordinate(self.width - 1, self.height - 1),
        }
        if corners & pattern_cells:
            return False

        center_x = {self.width // 2}
        center_y = {self.height // 2}
        if self.width % 2 == 0:
            center_x.add(self.width // 2 - 1)
        if self.height % 2 == 0:
            center_y.add(self.height // 2 - 1)
        centers = {
            Coordinate(x, y)
            for x in center_x
            for y in center_y
        }
        return bool(centers - pattern_cells)

    def _select_pattern_cells(
        self,
        entry: Coordinate,
        exit: Coordinate,
        perfect: bool = True,
    ) -> set[Coordinate] | None:
        """Select a pattern placement satisfying the generation mode."""
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

            if (
                not perfect
                and not self._pattern_preserves_non_perfect_terminals(
                    pattern_cells
                )
            ):
                continue

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
        perfect: bool = True,
    ) -> set[Coordinate]:
        """Reserve the selected 42 cells in the maze."""
        pattern_cells = self._select_pattern_cells(
            entry,
            exit,
            perfect=perfect,
        )

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
        on_step: GenerationStep | None = None,
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
            if on_step is not None:
                on_step(maze.grid)
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
        on_step: GenerationStep | None = None,
    ) -> GeneratedMaze:
        """Generate a maze and optionally report each carving step."""
        if not isinstance(perfect, bool):
            raise TypeError("perfect must be a bool")
        if on_step is not None and not callable(on_step):
            raise TypeError("on_step must be callable or None")
        self._random = random.Random(self.seed)
        if not perfect:
            return self._generate_non_perfect(entry, exit, on_step)

        return self._generate_perfect(entry, exit, on_step=on_step)

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

    def _passage_degrees(
        self,
        maze: Maze,
        playable_cells: set[Coordinate],
    ) -> dict[Coordinate, int]:
        """Return current passage degrees for playable cells."""
        degrees: dict[Coordinate, int] = {}
        for position in playable_cells:
            degree = 0
            for direction, (dx, dy) in DIRECTION_STEPS.items():
                neighbour = Coordinate(
                    position.x + dx,
                    position.y + dy,
                )
                if (
                    neighbour in playable_cells
                    and not maze.get_walls(position) & direction
                ):
                    degree += 1
            degrees[position] = degree
        return degrees

    def _keeps_open_area_constraint(
        self,
        maze: Maze,
        position: Coordinate,
        direction: Wall,
    ) -> bool:
        """Return whether an opening avoids a fully open 3x3 area."""
        origins_x = range(
            max(0, position.x - 2),
            min(self.width - 3, position.x) + 1,
        )
        origins_y = range(
            max(0, position.y - 2),
            min(self.height - 3, position.y) + 1,
        )

        def is_open(cell: Coordinate, wall: Wall) -> bool:
            if cell == position and wall == direction:
                return True
            return not maze.get_walls(cell) & wall

        for origin_y in origins_y:
            for origin_x in origins_x:
                all_east_open = all(
                    is_open(
                        Coordinate(cell_x, cell_y),
                        Wall.EAST,
                    )
                    for cell_y in range(origin_y, origin_y + 3)
                    for cell_x in range(origin_x, origin_x + 2)
                )
                all_south_open = all(
                    is_open(
                        Coordinate(cell_x, cell_y),
                        Wall.SOUTH,
                    )
                    for cell_y in range(origin_y, origin_y + 2)
                    for cell_x in range(origin_x, origin_x + 3)
                )
                if all_east_open and all_south_open:
                    return False
        return True

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
        on_step: GenerationStep | None = None,
    ) -> GeneratedMaze:
        """Generate a connected maze with multiple independent routes."""
        result = self._generate_perfect(
            entry,
            exit,
            validate_as_perfect=False,
            on_step=on_step,
        )
        playable_cells = self._playable_cells(set(result.pattern_cells))
        degrees = self._passage_degrees(result.maze, playable_cells)
        dead_end_count = sum(degree == 1 for degree in degrees.values())
        loop_count = 0

        # Opening an edge only removes that edge from the closed-edge set.
        # The dead-end score changes only for edges incident to one of the
        # two cells whose degree was changed, so keep a heap and refresh that
        # small neighbourhood after each opening.
        active_edges = {
            (position, direction)
            for position, direction in self._candidate_edges(
                result.maze,
                playable_cells,
            )
            if self._keeps_open_area_constraint(
                result.maze,
                position,
                direction,
            )
        }
        incident_edges: dict[
            Coordinate,
            set[tuple[Coordinate, Wall]],
        ] = {cell: set() for cell in playable_cells}
        for edge in active_edges:
            position, direction = edge
            dx, dy = DIRECTION_STEPS[direction]
            neighbour = Coordinate(position.x + dx, position.y + dy)
            incident_edges[position].add(edge)
            incident_edges[neighbour].add(edge)

        def edge_neighbour(
            edge: tuple[Coordinate, Wall],
        ) -> Coordinate:
            position, direction = edge
            dx, dy = DIRECTION_STEPS[direction]
            return Coordinate(position.x + dx, position.y + dy)

        def edge_score(
            edge: tuple[Coordinate, Wall],
        ) -> tuple[int, int, int, int]:
            position, _ = edge
            neighbour = edge_neighbour(edge)
            dead_end_delta = 0
            for cell in (position, neighbour):
                dead_end_delta -= degrees[cell] == 1
                dead_end_delta += degrees[cell] + 1 == 1
            return (
                dead_end_delta,
                position.y,
                position.x,
                int(edge[1]),
            )

        scores = {edge: edge_score(edge) for edge in active_edges}
        heap: list[
            tuple[tuple[int, int, int, int], tuple[Coordinate, Wall]]
        ] = [
            (score, edge)
            for edge, score in scores.items()
        ]
        heapq.heapify(heap)

        while True:
            if (
                loop_count >= 2
                and dead_end_count <= 2
            ):
                break

            while heap:
                score, edge = heapq.heappop(heap)
                if (
                    edge in active_edges
                    and scores.get(edge) == score
                ):
                    if self._keeps_open_area_constraint(
                        result.maze,
                        edge[0],
                        edge[1],
                    ):
                        break
                    # Another opening may have made this edge violate the
                    # 3x3 constraint.  It cannot become valid again because
                    # openings only add passages, so discard it permanently.
                    active_edges.remove(edge)
                    del scores[edge]
            else:
                break

            position, direction = edge
            neighbour = edge_neighbour(edge)
            dead_end_count -= degrees[position] == 1
            dead_end_count -= degrees[neighbour] == 1
            result.maze.open_wall(position, direction)
            if on_step is not None:
                on_step(result.maze.grid)
            degrees[position] += 1
            degrees[neighbour] += 1
            dead_end_count += degrees[position] == 1
            dead_end_count += degrees[neighbour] == 1
            loop_count += 1

            active_edges.remove(edge)
            del scores[edge]
            for cell in (position, neighbour):
                for affected_edge in incident_edges[cell]:
                    if affected_edge not in active_edges:
                        continue
                    updated_score = edge_score(affected_edge)
                    scores[affected_edge] = updated_score
                    heapq.heappush(heap, (updated_score, affected_edge))

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
        validate_as_perfect: bool = True,
        on_step: GenerationStep | None = None,
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
            perfect=validate_as_perfect,
        )
        playable_cells = self._playable_cells(pattern_cells)
        self._carve_tree(maze, playable_cells, entry, on_step)

        result = GeneratedMaze(
            maze=maze,
            entry=entry,
            exit=exit,
            seed=self.seed,
            pattern_omitted=not pattern_cells,
        )

        if not validate_as_perfect:
            return result

        report = self._validation_report(result, perfect=True)

        if not report.is_valid:
            raise RuntimeError(
                "generated maze failed validation: "
                + "; ".join(report.errors)
            )

        return result
