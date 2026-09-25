"""Command-line entrypoint for the maze application."""

import sys
from collections.abc import Sequence


from config import ConfigError
from maze_setup import load_maze_setup


def a_maze_ing(argv: Sequence[str] | None = None) -> int:
    """Load configuration and initialize the maze model from the CLI."""
    arguments = sys.argv[1:] if argv is None else list(argv)

    if len(arguments) != 1:
        print("usage: python3 a_maze_ing.py config.txt", file=sys.stderr)
        return 2

    try:
        setup = load_maze_setup(arguments[0])
    except ConfigError as error:
        print(f"configuration error: {error}", file=sys.stderr)
        return 1

    print("Configuration loaded successfully.")
    print(f"Maze size: {setup.maze.width} x {setup.maze.height}")
    print(f"Entry: ({setup.entry.x}, {setup.entry.y})")
    print(f"Exit: ({setup.exit.x}, {setup.exit.y})")
    print(f"Perfect: {setup.perfect}")
    print(f"Seed: {setup.seed}")
    print("Maze data initialized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(a_maze_ing())
