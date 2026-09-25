"""Serialize generated mazes to the subject output format."""

from maze_generator import GeneratedMaze


def serialize_maze(
    result: GeneratedMaze,
    solution: str,
) -> str:
    """Return a generated maze and solution in output-file format."""
    if not isinstance(result, GeneratedMaze):
        raise TypeError("result must be a GeneratedMaze")
    if not isinstance(solution, str):
        raise TypeError("solution must be a string")
    if any(symbol not in "NESW" for symbol in solution):
        raise ValueError("solution must contain only NESW characters")

    grid_lines = [
        "".join(format(int(cell), "x") for cell in row)
        for row in result.grid
    ]
    footer = [
        f"{result.entry.x},{result.entry.y}",
        f"{result.exit.x},{result.exit.y}",
        solution,
    ]

    return "\n".join(
        grid_lines + [""] + footer
    ) + "\n"
