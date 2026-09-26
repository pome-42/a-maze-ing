"""Tests for shortest path search through maze walls."""

from unittest import TestCase

from maze import Maze
from maze_solver import shortest_path
from maze_types import Coordinate, Wall


class MazeSolverTests(TestCase):
    """Verify shortest path search and its input contract."""

    def test_finds_path_in_direction_order(self) -> None:
        maze = Maze(2, 2)
        maze.open_wall(Coordinate(0, 0), Wall.EAST)
        maze.open_wall(Coordinate(1, 0), Wall.SOUTH)

        self.assertEqual(
            shortest_path(maze, Coordinate(0, 0), Coordinate(1, 1)),
            "ES",
        )

    def test_selects_shortest_of_multiple_paths(self) -> None:
        maze = Maze(3, 2)
        maze.open_wall(Coordinate(0, 0), Wall.EAST)
        maze.open_wall(Coordinate(1, 0), Wall.EAST)
        maze.open_wall(Coordinate(0, 0), Wall.SOUTH)
        maze.open_wall(Coordinate(1, 1), Wall.EAST)
        maze.open_wall(Coordinate(2, 1), Wall.NORTH)

        self.assertEqual(
            shortest_path(maze, Coordinate(0, 0), Coordinate(2, 0)),
            "EE",
        )

    def test_rejects_unreachable_exit(self) -> None:
        with self.assertRaises(ValueError):
            shortest_path(Maze(2, 2), Coordinate(0, 0), Coordinate(1, 1))

    def test_same_entry_and_exit_returns_empty_path(self) -> None:
        self.assertEqual(
            shortest_path(Maze(2, 2), Coordinate(0, 0), Coordinate(0, 0)),
            "",
        )

    def test_does_not_mutate_maze(self) -> None:
        maze = Maze(2, 1)
        maze.open_wall(Coordinate(0, 0), Wall.EAST)
        before = maze.grid

        shortest_path(maze, Coordinate(0, 0), Coordinate(1, 0))

        self.assertEqual(maze.grid, before)
