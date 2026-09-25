"""Tests for Maze wall operations."""

from unittest import TestCase

from maze import Maze
from maze_types import ALL_WALLS, Coordinate, Wall


class WallOperationTests(TestCase):
    """Test opening walls and preserving wall invariants."""

    def test_open_east_wall_updates_both_cells(self) -> None:
        maze = Maze(width=3, height=3)
        position = Coordinate(1, 1)
        neighbour = Coordinate(2, 1)

        maze.open_wall(position, Wall.EAST)

        self.assertFalse(maze.get_walls(position) & Wall.EAST)
        self.assertFalse(maze.get_walls(neighbour) & Wall.WEST)

    def test_open_west_wall_updates_both_cells(self) -> None:
        maze = Maze(width=3, height=3)
        position = Coordinate(1, 1)
        neighbour = Coordinate(0, 1)

        maze.open_wall(position, Wall.WEST)

        self.assertFalse(maze.get_walls(position) & Wall.WEST)
        self.assertFalse(maze.get_walls(neighbour) & Wall.EAST)

    def test_open_south_wall_updates_both_cells(self) -> None:
        maze = Maze(width=3, height=3)
        position = Coordinate(1, 1)
        neighbour = Coordinate(1, 2)

        maze.open_wall(position, Wall.SOUTH)

        self.assertFalse(maze.get_walls(position) & Wall.SOUTH)
        self.assertFalse(maze.get_walls(neighbour) & Wall.NORTH)

    def test_open_north_wall_updates_both_cells(self) -> None:
        maze = Maze(width=3, height=3)
        position = Coordinate(1, 1)
        neighbour = Coordinate(1, 0)

        maze.open_wall(position, Wall.NORTH)

        self.assertFalse(maze.get_walls(position) & Wall.NORTH)
        self.assertFalse(maze.get_walls(neighbour) & Wall.SOUTH)

    def test_open_wall_preserves_other_walls(self) -> None:
        maze = Maze(width=3, height=3)
        position = Coordinate(1, 1)

        maze.open_wall(position, Wall.EAST)

        self.assertEqual(
            maze.get_walls(position),
            ALL_WALLS & ~Wall.EAST,
        )

    def test_outer_boundary_is_rejected(self) -> None:
        cases = (
            (Coordinate(1, 0), Wall.NORTH),
            (Coordinate(2, 1), Wall.EAST),
            (Coordinate(1, 2), Wall.SOUTH),
            (Coordinate(0, 1), Wall.WEST),
        )

        for position, direction in cases:
            with self.subTest(position=position, direction=direction):
                maze = Maze(width=3, height=3)
                initial_grid = [[ALL_WALLS] * 3 for _ in range(3)]

                with self.assertRaises(ValueError):
                    maze.open_wall(position, direction)

                self.assertEqual(maze.grid, initial_grid)

    def test_out_of_bounds_position_is_rejected(self) -> None:
        maze = Maze(width=3, height=3)

        with self.assertRaises(IndexError):
            maze.open_wall(Coordinate(3, 1), Wall.WEST)

    def test_compound_direction_is_rejected(self) -> None:
        maze = Maze(width=3, height=3)

        with self.assertRaises(ValueError):
            maze.open_wall(Coordinate(1, 1), Wall.NORTH | Wall.EAST)

    def test_integer_direction_is_rejected(self) -> None:
        maze = Maze(width=3, height=3)

        with self.assertRaises(ValueError):
            maze.open_wall(Coordinate(1, 1), 1)  # type: ignore[arg-type]

    def test_pattern_cell_is_rejected(self) -> None:
        maze = Maze(width=3, height=3)
        position = Coordinate(1, 1)
        maze.reserve_pattern_cells({position})

        with self.assertRaises(ValueError):
            maze.open_wall(position, Wall.EAST)

    def test_neighbouring_pattern_cell_is_rejected(self) -> None:
        maze = Maze(width=3, height=3)
        neighbour = Coordinate(2, 1)
        maze.reserve_pattern_cells({neighbour})

        with self.assertRaises(ValueError):
            maze.open_wall(Coordinate(1, 1), Wall.EAST)
