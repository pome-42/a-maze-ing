"""Tests for Maze wall operations."""

from unittest import TestCase

from maze import Maze
from maze_types import ALL_WALLS, Coordinate, Wall


class WallOperationTests(TestCase):
    """Test opening walls and preserving wall invariants."""

    def test_open_wall_updates_both_cells_for_each_direction(self) -> None:
        cases = (
            (
                Wall.EAST,
                Coordinate(2, 1),
                Wall.NORTH | Wall.SOUTH | Wall.WEST,
                Wall.NORTH | Wall.EAST | Wall.SOUTH,
            ),
            (
                Wall.WEST,
                Coordinate(0, 1),
                Wall.NORTH | Wall.EAST | Wall.SOUTH,
                Wall.NORTH | Wall.SOUTH | Wall.WEST,
            ),
            (
                Wall.SOUTH,
                Coordinate(1, 2),
                Wall.NORTH | Wall.EAST | Wall.WEST,
                Wall.EAST | Wall.SOUTH | Wall.WEST,
            ),
            (
                Wall.NORTH,
                Coordinate(1, 0),
                Wall.EAST | Wall.SOUTH | Wall.WEST,
                Wall.NORTH | Wall.EAST | Wall.WEST,
            ),
        )

        for (
            direction,
            neighbour,
            expected_position,
            expected_neighbour,
        ) in cases:
            with self.subTest(direction=direction):
                maze = Maze(width=3, height=3)
                position = Coordinate(1, 1)
                unrelated = Coordinate(0, 0)

                maze.open_wall(position, direction)

                self.assertEqual(
                    maze.get_walls(position),
                    expected_position,
                )
                self.assertEqual(
                    maze.get_walls(neighbour),
                    expected_neighbour,
                )
                self.assertEqual(maze.get_walls(unrelated), ALL_WALLS)

    def test_opening_same_wall_twice_is_idempotent(self) -> None:
        maze = Maze(width=3, height=3)
        position = Coordinate(1, 1)

        maze.open_wall(position, Wall.EAST)
        first_grid = [row[:] for row in maze.grid]

        maze.open_wall(position, Wall.EAST)

        self.assertEqual(maze.grid, first_grid)

    def test_opening_two_directions_accumulates(self) -> None:
        maze = Maze(width=3, height=3)
        position = Coordinate(1, 1)

        maze.open_wall(position, Wall.EAST)
        maze.open_wall(position, Wall.SOUTH)

        self.assertEqual(maze.get_walls(position), Wall.NORTH | Wall.WEST)
        self.assertEqual(
            maze.get_walls(Coordinate(2, 1)),
            Wall.NORTH | Wall.EAST | Wall.SOUTH,
        )
        self.assertEqual(
            maze.get_walls(Coordinate(1, 2)),
            Wall.EAST | Wall.SOUTH | Wall.WEST,
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
        initial_grid = [row[:] for row in maze.grid]
        initial_pattern_cells = maze.pattern_cells

        with self.assertRaises(ValueError):
            maze.open_wall(position, Wall.EAST)

        self.assertEqual(maze.grid, initial_grid)
        self.assertEqual(maze.pattern_cells, initial_pattern_cells)

    def test_neighbouring_pattern_cell_is_rejected(self) -> None:
        maze = Maze(width=3, height=3)
        neighbour = Coordinate(2, 1)
        maze.reserve_pattern_cells({neighbour})
        initial_grid = [row[:] for row in maze.grid]
        initial_pattern_cells = maze.pattern_cells

        with self.assertRaises(ValueError):
            maze.open_wall(Coordinate(1, 1), Wall.EAST)

        self.assertEqual(maze.grid, initial_grid)
        self.assertEqual(maze.pattern_cells, initial_pattern_cells)
