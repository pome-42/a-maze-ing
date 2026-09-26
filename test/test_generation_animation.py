"""Tests for generation-step callbacks used by the animation branch."""

from unittest import TestCase

from mazegen import MazeGenerator


class GenerationAnimationTests(TestCase):
    """Verify callbacks receive immutable intermediate grid snapshots."""

    def test_callback_receives_steps_before_final_result(self) -> None:
        steps: list[tuple[tuple[object, ...], ...]] = []
        result = MazeGenerator(10, 8, seed=42).generate(
            on_step=steps.append,
        )

        self.assertGreater(len(steps), 1)
        self.assertEqual(steps[-1], result.grid)
        self.assertIsNot(steps[-1], result.grid)

    def test_non_perfect_generation_reports_extra_openings(self) -> None:
        steps: list[tuple[tuple[object, ...], ...]] = []
        result = MazeGenerator(10, 8, seed=42, perfect=False).generate(
            on_step=steps.append,
        )

        self.assertGreater(len(steps), 1)
        self.assertEqual(steps[-1], result.grid)
