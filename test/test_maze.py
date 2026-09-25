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

    def test_grid_is_read_only(self) -> None:
        maze = Maze(width=4, height=2)

        with self.assertRaises(TypeError):
            maze.grid[0][0] = Wall.NORTH  # type: ignore[index]

        with self.assertRaises(TypeError):
            maze.grid[0] = (Wall.NORTH,) * 4  # type: ignore[index]

    def test_dimensions_are_read_only(self) -> None:
        maze = Maze(width=4, height=2)

        with self.assertRaises(AttributeError):
            maze.width = 5  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            maze.height = 3  # type: ignore[misc]

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

    def test_reserving_pattern_cells_replaces_existing_reservation(
        self,
    ) -> None:
        maze = Maze(width=4, height=2)
        first_cells = {Coordinate(0, 0)}
        second_cells = {Coordinate(1, 0), Coordinate(2, 1)}

        maze.reserve_pattern_cells(first_cells)
        maze.reserve_pattern_cells(second_cells)

        self.assertEqual(maze.pattern_cells, second_cells)

    def test_reregistering_same_pattern_cells_is_idempotent(self) -> None:
        maze = Maze(width=4, height=2)
        cells = {Coordinate(1, 0), Coordinate(2, 1)}

        maze.reserve_pattern_cells(cells)
        first_snapshot = maze.pattern_cells
        maze.reserve_pattern_cells(cells)

        self.assertEqual(maze.pattern_cells, first_snapshot)

    def test_reserving_empty_pattern_cells_clears_reservation(self) -> None:
        maze = Maze(width=4, height=2)
        maze.reserve_pattern_cells({Coordinate(1, 0)})

        maze.reserve_pattern_cells(set())

        self.assertEqual(maze.pattern_cells, frozenset())

    def test_out_of_bounds_pattern_cell_is_rejected_atomically(self) -> None:
        maze = Maze(width=4, height=2)
        maze.reserve_pattern_cells({Coordinate(0, 0)})
        initial_grid = maze.grid
        initial_pattern_cells = maze.pattern_cells

        with self.assertRaises(ValueError):
            maze.reserve_pattern_cells({Coordinate(1, 0), Coordinate(4, 0)})

        self.assertEqual(maze.grid, initial_grid)
        self.assertEqual(maze.pattern_cells, initial_pattern_cells)

    def test_open_pattern_cell_is_rejected_atomically(self) -> None:
        maze = Maze(width=4, height=2)
        maze.reserve_pattern_cells({Coordinate(0, 0)})
        maze.open_wall(Coordinate(1, 0), Wall.SOUTH)
        initial_grid = maze.grid
        initial_pattern_cells = maze.pattern_cells

        with self.assertRaises(ValueError):
            maze.reserve_pattern_cells({Coordinate(0, 0), Coordinate(1, 0)})

        self.assertEqual(maze.grid, initial_grid)
        self.assertEqual(maze.pattern_cells, initial_pattern_cells)

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
        position = Coordinate(2, 1)
        maze.open_wall(position, Wall.EAST)

        self.assertEqual(maze.get_walls(position), ALL_WALLS & ~Wall.EAST)

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
