"""Public, reusable API for generating validated mazes."""

from dataclasses import dataclass

from maze_generator import (
    GeneratedMaze as _GeneratedMaze,
    MazeGenerator as _MazeGenerator,
)
from maze_solver import shortest_path
from maze_types import Coordinate, Wall

__all__ = ["Coordinate", "MazeGenerator", "MazeResult", "Wall"]


@dataclass(frozen=True, slots=True)
class MazeResult:
    """Expose an immutable generated structure and one shortest solution."""

    grid: tuple[tuple[Wall, ...], ...]
    entry: Coordinate
    exit: Coordinate
    pattern_cells: frozenset[Coordinate]
    seed: int
    solution: str
    pattern_omitted: bool

    @property
    def width(self) -> int:
        """Return the generated maze width."""
        return len(self.grid[0]) if self.grid else 0

    @property
    def height(self) -> int:
        """Return the generated maze height."""
        return len(self.grid)


class MazeGenerator:
    """Generate a reusable maze without requiring the CLI or MLX display.

    ``entry`` and ``exit`` use ``(x, y)`` coordinates.  If omitted, the
    default terminals are the top-left and bottom-right cells.
    """

    def __init__(
        self,
        width: int,
        height: int,
        *,
        seed: int | None = None,
        entry: Coordinate | tuple[int, int] | None = None,
        exit: Coordinate | tuple[int, int] | None = None,
        perfect: bool = True,
        algorithm: str = "dfs",
    ) -> None:
        self._validate_bool(perfect, "perfect")
        self._core = _MazeGenerator(
            width,
            height,
            seed=seed,
            algorithm=algorithm,
        )
        self._entry = self._coordinate_or_default(entry, Coordinate(0, 0))
        self._exit = self._coordinate_or_default(
            exit,
            Coordinate(width - 1, height - 1),
        )
        self._perfect = perfect

        if not self._core.width > self._entry.x >= 0:
            raise ValueError("entry must be inside the maze bounds")
        if not self._core.height > self._entry.y >= 0:
            raise ValueError("entry must be inside the maze bounds")
        if not self._core.width > self._exit.x >= 0:
            raise ValueError("exit must be inside the maze bounds")
        if not self._core.height > self._exit.y >= 0:
            raise ValueError("exit must be inside the maze bounds")
        if self._entry == self._exit:
            raise ValueError("entry and exit must be different")

    @staticmethod
    def _validate_bool(value: bool, name: str) -> None:
        if not isinstance(value, bool):
            raise TypeError(f"{name} must be a boolean")

    @staticmethod
    def _coordinate_or_default(
        value: Coordinate | tuple[int, int] | None,
        default: Coordinate,
    ) -> Coordinate:
        if value is None:
            return default
        if isinstance(value, Coordinate):
            return value
        if (
            isinstance(value, tuple)
            and len(value) == 2
            and not isinstance(value[0], bool)
            and not isinstance(value[1], bool)
            and isinstance(value[0], int)
            and isinstance(value[1], int)
        ):
            return Coordinate(*value)
        raise TypeError("coordinates must be Coordinate or (x, y) tuple")

    @staticmethod
    def _result(
        generated: _GeneratedMaze,
        solution: str,
    ) -> MazeResult:
        return MazeResult(
            grid=generated.grid,
            entry=generated.entry,
            exit=generated.exit,
            pattern_cells=generated.pattern_cells,
            seed=generated.seed,
            solution=solution,
            pattern_omitted=generated.pattern_omitted,
        )

    def generate(self) -> MazeResult:
        """Generate, validate, and solve a maze using the configured values."""
        generated = self._core.generate(
            self._entry,
            self._exit,
            perfect=self._perfect,
        )
        solution = shortest_path(
            generated.maze,
            generated.entry,
            generated.exit,
        )
        return self._result(generated, solution)
