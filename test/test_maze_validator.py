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


class MazeValidatorTests(TestCase):
    """Test basic grid and wall invariants."""

    def test_closed_grid_with_valid_metadata_is_accepted(self) -> None:
        report = validate_maze(_input(_closed_grid()))

        self.assertTrue(report.is_valid)
        self.assertEqual(report.errors, ())

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
