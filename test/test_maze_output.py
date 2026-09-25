"""Tests for maze output serialization."""

from unittest import TestCase

from maze import Maze
from maze_generator import GeneratedMaze
from maze_output import serialize_maze
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
