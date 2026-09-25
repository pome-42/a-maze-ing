"""Tests for independent grid and wall validation."""

from unittest import TestCase

from maze_types import ALL_WALLS, Coordinate, Wall
from maze_validator import MazeValidationInput, validate_maze


def _closed_grid(
    width: int = 3,
    height: int = 3,
) -> tuple[tuple[Wall, ...], ...]:
    """Return a hand-built all-closed grid snapshot."""
    return tuple(
        tuple(ALL_WALLS for _ in range(width))
        for _ in range(height)
    )


def _input(
    grid: tuple[tuple[Wall, ...], ...] | tuple[tuple[object, ...], ...],
    *,
    width: int = 3,
    height: int = 3,
    entry: Coordinate = Coordinate(0, 0),
    exit: Coordinate = Coordinate(2, 2),
    pattern_cells: frozenset[Coordinate] = frozenset(),
) -> MazeValidationInput:
    """Build validator input, including intentionally invalid snapshots."""
    return MazeValidationInput(
        grid=grid,  # type: ignore[arg-type]
        width=width,
        height=height,
        entry=entry,
        exit=exit,
        pattern_cells=pattern_cells,
        perfect=True,
    )


def _connected_tree_grid() -> tuple[tuple[Wall, ...], ...]:
    """Return a connected 3x3 tree with closed outer walls."""
    grid = [list(row) for row in _closed_grid()]
    for x in (0, 1):
        grid[0][x] &= ~Wall.EAST
        grid[0][x + 1] &= ~Wall.WEST
    grid[0][2] &= ~Wall.SOUTH
    grid[1][2] &= ~Wall.NORTH
    for x in (2, 1):
        grid[1][x] &= ~Wall.WEST
        grid[1][x - 1] &= ~Wall.EAST
    grid[1][0] &= ~Wall.SOUTH
    grid[2][0] &= ~Wall.NORTH
    for x in (0, 1):
        grid[2][x] &= ~Wall.EAST
        grid[2][x + 1] &= ~Wall.WEST
    return tuple(tuple(row) for row in grid)


def _fully_open_grid(
    width: int,
    height: int,
) -> tuple[tuple[Wall, ...], ...]:
    """Return a grid with all internal edges open."""
    grid = [list(row) for row in _closed_grid(width, height)]
    for y in range(height):
        for x in range(width - 1):
            grid[y][x] &= ~Wall.EAST
            grid[y][x + 1] &= ~Wall.WEST
    for y in range(height - 1):
        for x in range(width):
            grid[y][x] &= ~Wall.SOUTH
            grid[y + 1][x] &= ~Wall.NORTH
    return tuple(tuple(row) for row in grid)


class MazeValidatorTests(TestCase):
    """Test basic grid and wall invariants."""

    def test_closed_grid_with_valid_metadata_is_accepted(self) -> None:
        report = validate_maze(_input(_connected_tree_grid()))

        self.assertTrue(report.is_valid)
        self.assertEqual(report.errors, ())

    def test_unreachable_passage_cells_are_rejected(self) -> None:
        report = validate_maze(_input(_closed_grid()))

        self.assertFalse(report.is_valid)
        self.assertEqual(report.vertex_count, 9)
        self.assertEqual(report.edge_count, 0)
        self.assertTrue(
            any("is unreachable" in error for error in report.errors)
        )

    def test_three_by_three_fully_open_area_is_rejected(self) -> None:
        report = validate_maze(_input(_fully_open_grid(3, 3)))

        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("3x3 fully open area" in error for error in report.errors)
        )

    def test_two_by_three_and_three_by_two_open_areas_are_allowed(
        self,
    ) -> None:
        for width, height in ((2, 3), (3, 2)):
            with self.subTest(width=width, height=height):
                data = _input(
                    _fully_open_grid(width, height),
                    width=width,
                    height=height,
                    exit=Coordinate(width - 1, height - 1),
                )

                report = validate_maze(data)

                self.assertTrue(report.is_valid)

    def test_grid_shape_must_match_declared_dimensions(self) -> None:
        data = _input(_closed_grid(2, 3), width=3)

        report = validate_maze(data)

        self.assertFalse(report.is_valid)
        self.assertTrue(any("grid row 0" in error for error in report.errors))

    def test_cells_must_be_wall_values(self) -> None:
        grid = list(map(list, _closed_grid()))
        grid[1][1] = 16  # type: ignore[call-overload]

        report = validate_maze(_input(tuple(tuple(row) for row in grid)))

        self.assertFalse(report.is_valid)
        self.assertTrue(any("cell (1, 1)" in error for error in report.errors))

    def test_outer_boundary_opening_is_rejected(self) -> None:
        grid = [list(row) for row in _closed_grid()]
        grid[0][1] &= ~Wall.NORTH

        report = validate_maze(_input(tuple(tuple(row) for row in grid)))

        self.assertFalse(report.is_valid)
        self.assertTrue(any("outer NORTH" in error for error in report.errors))

    def test_adjacent_wall_mismatch_is_rejected(self) -> None:
        grid = [list(row) for row in _closed_grid()]
        grid[1][1] &= ~Wall.EAST

        report = validate_maze(_input(tuple(tuple(row) for row in grid)))

        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("east/west walls disagree" in error for error in report.errors)
        )

    def test_reserved_cell_must_be_closed_and_not_entry_or_exit(self) -> None:
        grid = [list(row) for row in _closed_grid()]
        grid[1][1] &= ~Wall.EAST
        reserved = frozenset({Coordinate(1, 1), Coordinate(0, 0)})

        report = validate_maze(
            _input(
                tuple(tuple(row) for row in grid),
                pattern_cells=reserved,
            )
        )

        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("not fully closed" in error for error in report.errors)
        )
        self.assertTrue(
            any("overlaps entry" in error for error in report.errors)
        )

    def test_invalid_coordinates_are_reported(self) -> None:
        data = _input(_closed_grid(), entry=Coordinate(-1, 0))

        report = validate_maze(data)

        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("entry is outside" in error for error in report.errors)
        )

    def test_validation_does_not_change_input_snapshot(self) -> None:
        grid = _closed_grid()
        data = _input(grid)

        validate_maze(data)

        self.assertEqual(data.grid, grid)
