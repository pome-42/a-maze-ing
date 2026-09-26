"""Command-line entrypoint for the maze application."""

import sys
from collections.abc import Sequence
import secrets


from config import ConfigError
from maze_generator import GeneratedMaze, MazeGenerator
from maze_setup import MazeSetup, load_maze_setup
from maze_output import save_maze, serialize_maze
from maze_solver import shortest_path
from maze_validator import MazeValidationInput, validate_maze
from mlx_view import MlxView


def _generate_and_save(
    setup: MazeSetup,
    seed: int | None,
) -> tuple[GeneratedMaze, str]:
    """Generate, independently validate, solve, and save one maze."""
    if not isinstance(setup, MazeSetup):
        raise TypeError("setup must be a MazeSetup")

    generated = MazeGenerator(
        setup.maze.width,
        setup.maze.height,
        seed=seed,
    ).generate(
        setup.entry,
        setup.exit,
        perfect=setup.perfect,
    )
    report = validate_maze(
        MazeValidationInput(
            grid=generated.grid,
            width=generated.maze.width,
            height=generated.maze.height,
            entry=generated.entry,
            exit=generated.exit,
            pattern_cells=generated.pattern_cells,
            perfect=setup.perfect,
        )
    )
    if not report.is_valid:
        raise RuntimeError(
            "generated maze failed independent validation: "
            + "; ".join(report.errors)
        )

    solution = shortest_path(
        generated.maze,
        generated.entry,
        generated.exit,
    )
    save_maze(setup.output_file, serialize_maze(generated, solution))
    return generated, solution


def _print_generation_summary(generated: GeneratedMaze) -> None:
    """Print the seed and warning associated with a displayed maze."""
    if generated.pattern_omitted:
        print(
            "Warning: maze is too small for the 42 pattern; "
            "pattern omitted.",
            file=sys.stderr,
        )
    print(f"Seed: {generated.seed}")


def a_maze_ing(
    argv: Sequence[str] | None = None,
    display: bool | None = None,
) -> int:
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

    try:
        generated, solution = _generate_and_save(setup, setup.seed)
    except (OSError, RuntimeError, ValueError, TypeError) as error:
        print(f"generation error: {error}", file=sys.stderr)
        return 1

    _print_generation_summary(generated)

    print("Configuration loaded successfully.")
    print(f"Maze size: {generated.maze.width} x {generated.maze.height}")
    print(f"Entry: ({generated.entry.x}, {generated.entry.y})")
    print(f"Exit: ({generated.exit.x}, {generated.exit.y})")
    print(f"Perfect: {setup.perfect}")
    print("Maze data initialized.")
    print(f"Maze saved to: {setup.output_file}")

    should_display = (
        display if display is not None else sys.stdout.isatty()
    )
    if not should_display:
        return 0

    def regenerate() -> tuple[GeneratedMaze, str]:
        """Generate a fresh seed and persist it before redrawing."""
        next_seed = secrets.randbits(64)
        while next_seed == generated.seed:
            next_seed = secrets.randbits(64)
        new_generated, new_solution = _generate_and_save(setup, next_seed)
        _print_generation_summary(new_generated)
        return new_generated, new_solution

    try:
        MlxView(
            generated.maze.width,
            generated.maze.height,
            regenerate=regenerate,
        ).run(generated, solution)
    except (OSError, RuntimeError, ValueError, TypeError) as error:
        print(f"display error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(a_maze_ing())
