"""Tests for maze output serialization."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from maze import Maze
from maze_generator import GeneratedMaze
from maze_output import save_maze, serialize_maze
from maze_types import Coordinate, Wall


class MazeOutputTests(TestCase):
    """Verify the exact text output contract."""

    def test_serializes_grid_footer_and_final_newline(self) -> None:
        result = GeneratedMaze(
            maze=Maze(2, 2),
            entry=Coordinate(0, 0),
            exit=Coordinate(1, 1),
            seed=42,
            pattern_omitted=True,
        )

        self.assertEqual(
            serialize_maze(result, "ES"),
            "ff\nff\n\n0,0\n1,1\nES\n",
        )

    def test_serializes_open_wall_bits_as_lowercase_hex(self) -> None:
        maze = Maze(2, 1)
        maze.open_wall(Coordinate(0, 0), Wall.EAST)
        result = GeneratedMaze(
            maze=maze,
            entry=Coordinate(0, 0),
            exit=Coordinate(1, 0),
            seed=42,
            pattern_omitted=True,
        )

        self.assertEqual(
            serialize_maze(result, "E"),
            "d7\n\n0,0\n1,0\nE\n",
        )

    def test_rejects_invalid_result_and_solution(self) -> None:
        with self.assertRaises(TypeError):
            serialize_maze("invalid", "")  # type: ignore[arg-type]

        result = GeneratedMaze(
            maze=Maze(1, 1),
            entry=Coordinate(0, 0),
            exit=Coordinate(0, 0),
            seed=42,
            pattern_omitted=True,
        )
        with self.assertRaises(ValueError):
            serialize_maze(result, "X")

    def test_save_maze_writes_content_and_replaces_existing_file(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "maze.txt"
            path.write_text("old\n", encoding="utf-8")

            save_maze(str(path), "new\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "new\n")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_save_maze_cleans_temporary_file_when_replace_fails(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "maze.txt"
            path.write_text("old\n", encoding="utf-8")

            with patch(
                "maze_output.os.replace",
                side_effect=OSError("replace failed"),
            ):
                with self.assertRaises(OSError):
                    save_maze(str(path), "new\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "old\n")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_save_maze_rejects_invalid_arguments(self) -> None:
        with self.assertRaises(TypeError):
            save_maze(123, "content")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            save_maze("", "content")
        with self.assertRaises(TypeError):
            save_maze("maze.txt", 123)  # type: ignore[arg-type]
