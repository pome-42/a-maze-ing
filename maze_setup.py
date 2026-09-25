"""Connect validated configuration values to the initial maze model."""

from dataclasses import dataclass

from config import Config, load_config
from maze import Maze
from maze_types import Coordinate


@dataclass(frozen=True)
class MazeSetup:
    """Store an initial maze and the settings needed by later stages."""

    maze: Maze
    entry: Coordinate
    exit: Coordinate
    output_file: str
    perfect: bool
    seed: int | None


def create_maze_setup(config: Config) -> MazeSetup:
    """Create an initial maze and convert configuration coordinates."""
    if not isinstance(config, Config):
        raise TypeError("config must be a Config")

    maze = Maze(config.width, config.height)
    entry = Coordinate(*config.entry)
    exit_position = Coordinate(*config.exit)

    if not maze.in_bounds(entry):
        raise ValueError("entry coordinate must be within the maze bounds")
    if not maze.in_bounds(exit_position):
        raise ValueError("exit coordinate must be within the maze bounds")
    if entry == exit_position:
        raise ValueError("entry and exit must be different")
    if not isinstance(config.output_file, str) or not config.output_file:
        raise ValueError("output_file must not be empty")
    if not isinstance(config.perfect, bool):
        raise TypeError("perfect must be a bool")
    if config.seed is not None and (
        isinstance(config.seed, bool) or not isinstance(config.seed, int)
    ):
        raise TypeError("seed must be an integer or None")

    return MazeSetup(
        maze=maze,
        entry=entry,
        exit=exit_position,
        output_file=config.output_file,
        perfect=config.perfect,
        seed=config.seed,
    )


def load_maze_setup(path: str) -> MazeSetup:
    """Load a configuration file and create its initial maze setup."""
    return create_maze_setup(load_config(path))
