"""Command-line entrypoint for the maze application."""

import sys
from collections.abc import Sequence


from config import ConfigError
from maze_generator import MazeGenerator
from maze_setup import load_maze_setup
from maze_output import save_maze, serialize_maze
from maze_solver import shortest_path


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

    if not setup.perfect:
        print(
            "generation error: PERFECT=False is not supported yet; "
            "use PERFECT=True",
            file=sys.stderr,
        )
        return 1

    try:
        generated = MazeGenerator(
            setup.maze.width,
            setup.maze.height,
            seed=setup.seed,
        ).generate(setup.entry, setup.exit)
        solution = shortest_path(
            generated.maze,
            generated.entry,
            generated.exit,
        )
        content = serialize_maze(generated, solution)
        save_maze(setup.output_file, content)
    except (OSError, RuntimeError, ValueError, TypeError) as error:
        print(f"generation error: {error}", file=sys.stderr)
        return 1

    if generated.pattern_omitted:
        print(
            "Warning: maze is too small for the 42 pattern; "
            "pattern omitted.",
            file=sys.stderr,
        )

    print("Configuration loaded successfully.")
    print(f"Maze size: {generated.maze.width} x {generated.maze.height}")
    print(f"Entry: ({generated.entry.x}, {generated.entry.y})")
    print(f"Exit: ({generated.exit.x}, {generated.exit.y})")
    print("Perfect: True")
    print(f"Seed: {generated.seed}")
    print("Maze data initialized.")
    print(f"Maze saved to: {setup.output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(a_maze_ing())
