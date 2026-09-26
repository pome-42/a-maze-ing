"""Regression checks for the no-real-dead-end bonus branch."""

from unittest import TestCase

from maze_generator import MazeGenerator
from maze_validator import MazeValidationInput, validate_maze


class NoDeadEndsBonusTests(TestCase):
    """Keep the analyzer-compatible no-real-dead-end guarantee explicit."""

    def test_non_perfect_mazes_have_no_real_dead_ends(self) -> None:
        for width, height, seed in (
            (10, 8, 0),
            (10, 8, 42),
            (15, 15, 42),
            (25, 20, 42),
        ):
            with self.subTest(width=width, height=height, seed=seed):
                result = MazeGenerator(
                    width,
                    height,
                    seed=seed,
                ).generate(perfect=False)
                report = validate_maze(
                    MazeValidationInput(
                        grid=result.grid,
                        width=width,
                        height=height,
                        entry=result.entry,
                        exit=result.exit,
                        pattern_cells=result.pattern_cells,
                        perfect=False,
                    )
                )
                self.assertTrue(report.is_valid, report.errors)
                self.assertEqual(report.normal_dead_end_count, 0)
                self.assertGreaterEqual(report.total_dead_end_count, 0)
