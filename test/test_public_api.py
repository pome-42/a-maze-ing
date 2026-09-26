"""Tests for the installable reusable maze-generation API."""

from unittest import TestCase

from mazegen import MazeGenerator, MazeResult


class PublicApiTests(TestCase):
    """Verify that consumers can generate and inspect a maze."""

    def test_generates_structure_and_solution(self) -> None:
        result = MazeGenerator(10, 8, seed=42, perfect=False).generate()

        self.assertIsInstance(result, MazeResult)
        self.assertEqual((result.width, result.height), (10, 8))
        self.assertEqual(result.seed, 42)
        self.assertEqual(result.entry.as_tuple(), (0, 0))
        self.assertEqual(result.exit.as_tuple(), (9, 7))
        self.assertTrue(result.solution)

    def test_same_seed_reproduces_result(self) -> None:
        first = MazeGenerator(10, 8, seed=42, perfect=False).generate()
        second = MazeGenerator(10, 8, seed=42, perfect=False).generate()

        self.assertEqual(first, second)

    def test_accepts_tuple_terminals(self) -> None:
        result = MazeGenerator(
            10,
            8,
            seed=42,
            entry=(1, 1),
            exit=(8, 6),
        ).generate()

        self.assertEqual(result.entry.as_tuple(), (1, 1))
        self.assertEqual(result.exit.as_tuple(), (8, 6))
