"""Tests for the initial Maze model."""

from unittest import TestCase

from maze import Maze
from maze_types import ALL_WALLS, Coordinate, Wall


class MazeInitialStateTests(TestCase):
    """Test the initial state of a Maze."""

    def test_grid_has_requested_dimensions(self) -> None:
        maze = Maze(width=4, height=2)

        self.assertEqual(len(maze.grid), 2)
        self.assertTrue(all(len(row) == 4 for row in maze.grid))

    def test_all_cells_start_with_all_walls(self) -> None:
        maze = Maze(width=4, height=2)

        for row in maze.grid:
            for cell in row:
                self.assertIsInstance(cell, Wall)
                self.assertEqual(cell, ALL_WALLS)

    def test_grid_rows_are_independent(self) -> None:
        maze = Maze(width=4, height=2)

        maze.grid[0][0] = Wall.NORTH

        self.assertEqual(maze.grid[0][0], Wall.NORTH)
        self.assertEqual(maze.grid[1][0], ALL_WALLS)

    def test_pattern_cells_start_empty(self) -> None:
        maze = Maze(width=4, height=2)

        self.assertEqual(maze.pattern_cells, set())

    def test_pattern_cells_are_not_shared_between_mazes(self) -> None:
        first_maze = Maze(width=4, height=2)
        second_maze = Maze(width=4, height=2)

        first_maze.reserve_pattern_cells({Coordinate(0, 0)})

        self.assertIn(Coordinate(0, 0), first_maze.pattern_cells)
        self.assertNotIn(Coordinate(0, 0), second_maze.pattern_cells)

    def test_pattern_cells_are_read_only(self) -> None:
        maze = Maze(width=4, height=2)
        maze.reserve_pattern_cells({Coordinate(0, 0)})
        reserved = maze.pattern_cells

        with self.assertRaises(AttributeError):
            reserved.add(Coordinate(1, 0))  # type: ignore[attr-defined]

        with self.assertRaises(AttributeError):
            maze.pattern_cells = frozenset()  # type: ignore[misc]

    def test_pattern_cells_can_be_reserved(self) -> None:
        maze = Maze(width=4, height=2)
        cells = {Coordinate(1, 0), Coordinate(2, 1)}

        maze.reserve_pattern_cells(cells)

        self.assertEqual(maze.pattern_cells, cells)
        for position in cells:
            self.assertEqual(maze.get_walls(position), ALL_WALLS)

    def test_reserved_pattern_cells_are_copied(self) -> None:
        maze = Maze(width=4, height=2)
        cells = {Coordinate(1, 0)}

        maze.reserve_pattern_cells(cells)
        cells.add(Coordinate(2, 1))

        self.assertNotIn(Coordinate(2, 1), maze.pattern_cells)

    def test_out_of_bounds_pattern_cell_is_rejected_atomically(self) -> None:
        maze = Maze(width=4, height=2)
        maze.reserve_pattern_cells({Coordinate(0, 0)})

        with self.assertRaises(ValueError):
            maze.reserve_pattern_cells({Coordinate(1, 0), Coordinate(4, 0)})

        self.assertEqual(maze.pattern_cells, {Coordinate(0, 0)})

    def test_open_pattern_cell_is_rejected_atomically(self) -> None:
        maze = Maze(width=4, height=2)
        maze.grid[0][1] = Wall.NORTH
        maze.reserve_pattern_cells({Coordinate(0, 0)})

        with self.assertRaises(ValueError):
            maze.reserve_pattern_cells({Coordinate(0, 0), Coordinate(1, 0)})

        self.assertEqual(maze.pattern_cells, {Coordinate(0, 0)})

    def test_in_bounds_accepts_coordinates_inside_maze(self) -> None:
        maze = Maze(width=4, height=2)

        self.assertTrue(maze.in_bounds(Coordinate(0, 0)))
        self.assertTrue(maze.in_bounds(Coordinate(3, 1)))

    def test_in_bounds_rejects_coordinates_outside_maze(self) -> None:
        maze = Maze(width=4, height=2)

        self.assertFalse(maze.in_bounds(Coordinate(-1, 0)))
        self.assertFalse(maze.in_bounds(Coordinate(4, 0)))
        self.assertFalse(maze.in_bounds(Coordinate(0, -1)))
        self.assertFalse(maze.in_bounds(Coordinate(0, 2)))

    def test_get_walls_returns_walls_at_coordinate(self) -> None:
        maze = Maze(width=4, height=2)
        position = Coordinate(3, 1)
        maze.grid[position.y][position.x] = Wall.NORTH

        self.assertEqual(maze.get_walls(position), Wall.NORTH)

    def test_get_walls_rejects_coordinates_outside_maze(self) -> None:
        maze = Maze(width=4, height=2)

        with self.assertRaises(IndexError):
            maze.get_walls(Coordinate(-1, 0))
        with self.assertRaises(IndexError):
            maze.get_walls(Coordinate(4, 0))
        with self.assertRaises(IndexError):
            maze.get_walls(Coordinate(0, -1))
        with self.assertRaises(IndexError):
            maze.get_walls(Coordinate(0, 2))

    def test_zero_width_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Maze(width=0, height=2)

    def test_zero_height_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Maze(width=4, height=0)

    def test_negative_width_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Maze(width=-1, height=2)

    def test_negative_height_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Maze(width=2, height=-1)

    def test_non_integer_dimensions_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            Maze(width=1.5, height=2)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            Maze(width=2, height="2")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            Maze(width=True, height=2)
        with self.assertRaises(TypeError):
            Maze(width=2, height=False)
