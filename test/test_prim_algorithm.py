"""Tests for the second, Prim-based generation algorithm."""

from unittest import TestCase

from maze_generator import MazeGenerator
from maze_validator import MazeValidationInput, validate_maze


class PrimAlgorithmTests(TestCase):
    """Verify Prim output and deterministic selection."""

    def test_prim_generates_a_valid_perfect_maze(self) -> None:
        result = MazeGenerator(
            15,
            15,
            seed=42,
            algorithm="prim",
        ).generate()
        report = validate_maze(
            MazeValidationInput(
                grid=result.grid,
                width=15,
                height=15,
                entry=result.entry,
                exit=result.exit,
                pattern_cells=result.pattern_cells,
                perfect=True,
            )
        )
        self.assertTrue(report.is_valid, report.errors)

    def test_prim_is_reproducible_and_differs_from_dfs(self) -> None:
        first = MazeGenerator(15, 15, seed=42, algorithm="prim").generate()
        second = MazeGenerator(15, 15, seed=42, algorithm="prim").generate()
        dfs = MazeGenerator(15, 15, seed=42, algorithm="dfs").generate()

        self.assertEqual(first.grid, second.grid)
        self.assertNotEqual(first.grid, dfs.grid)
