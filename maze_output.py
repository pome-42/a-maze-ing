"""Serialize generated mazes to the subject output format."""

import os
from pathlib import Path
import tempfile

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


def save_maze(path: str, content: str) -> None:
    """Atomically save serialized maze content to a file."""
    if not isinstance(path, str):
        raise TypeError("path must be a string")
    if not path:
        raise ValueError("path must not be empty")
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    destination = Path(path)
    temporary_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, destination)
        temporary_path = None
    except OSError as error:
        raise OSError(
            f"failed to save maze to {destination}: {error}"
        ) from error
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
