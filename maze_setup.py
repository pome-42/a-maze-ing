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
