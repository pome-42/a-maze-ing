"""Tests for the maze generator entry point."""

from unittest import TestCase

from maze_generator import MazeGenerator
from maze_types import Coordinate


class MazeGeneratorTests(TestCase):
    """Verify validation of generator construction parameters."""

    def test_accepts_positive_dimensions_and_optional_seed(self) -> None:
        generator = MazeGenerator(10, 8, seed=42)

        self.assertEqual(generator.width, 10)
        self.assertEqual(generator.height, 8)
        self.assertEqual(generator.seed, 42)

    def test_accepts_seed_omission(self) -> None:
        generator = MazeGenerator(2, 2)

        self.assertIsNone(generator.seed)

    def test_rejects_non_integer_dimensions(self) -> None:
        with self.assertRaises(TypeError):
            MazeGenerator("10", 8)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            MazeGenerator(10, 8.0)  # type: ignore[arg-type]

    def test_rejects_boolean_dimensions(self) -> None:
        with self.assertRaises(TypeError):
            MazeGenerator(True, 8)
        with self.assertRaises(TypeError):
            MazeGenerator(10, False)

    def test_rejects_non_positive_dimensions(self) -> None:
        with self.assertRaises(ValueError):
            MazeGenerator(0, 8)
        with self.assertRaises(ValueError):
            MazeGenerator(10, -1)

    def test_rejects_invalid_seed(self) -> None:
        with self.assertRaises(TypeError):
            MazeGenerator(10, 8, seed=True)
        with self.assertRaises(TypeError):
            MazeGenerator(10, 8, seed="42")  # type: ignore[arg-type]

    def test_converts_mask_ones_to_coordinates(self) -> None:
        generator = MazeGenerator(10, 8)

        cells = generator._mask_cells(Coordinate(0, 0))

        expected = {
            Coordinate(0, 0),
            Coordinate(4, 0),
            Coordinate(5, 0),
            Coordinate(6, 0),
            Coordinate(0, 1),
            Coordinate(6, 1),
            Coordinate(0, 2),
            Coordinate(1, 2),
            Coordinate(2, 2),
            Coordinate(4, 2),
            Coordinate(5, 2),
            Coordinate(6, 2),
            Coordinate(2, 3),
            Coordinate(4, 3),
            Coordinate(2, 4),
            Coordinate(4, 4),
            Coordinate(5, 4),
            Coordinate(6, 4),
        }

        self.assertEqual(cells, expected)

    def test_mask_coordinates_follow_origin_offset(self) -> None:
        generator = MazeGenerator(10, 8)

        cells = generator._mask_cells(Coordinate(2, 3))

        self.assertIn(Coordinate(2, 3), cells)
        self.assertIn(Coordinate(8, 7), cells)
        self.assertNotIn(Coordinate(0, 0), cells)

    def test_mask_fits_inside_the_maze(self) -> None:
        generator = MazeGenerator(10, 8)

        self.assertTrue(generator._mask_fits(Coordinate(0, 0)))
        self.assertTrue(generator._mask_fits(Coordinate(3, 3)))

    def test_mask_does_not_fit_when_it_exceeds_the_maze(self) -> None:
        generator = MazeGenerator(6, 8)

        self.assertFalse(generator._mask_fits(Coordinate(0, 0)))
        self.assertFalse(generator._mask_fits(Coordinate(4, 3)))

    def test_candidate_origins_cover_all_fitting_positions_in_order(
        self,
    ) -> None:
        generator = MazeGenerator(10, 8)

        origins = generator._candidate_origins()

        expected = [
            Coordinate(x, y)
            for y in range(4)
            for x in range(4)
        ]
        self.assertEqual(origins, expected)

    def test_candidate_origins_are_empty_when_mask_does_not_fit(self) -> None:
        self.assertEqual(
            MazeGenerator(6, 8)._candidate_origins(),
            [],
        )

    def test_exact_fit_has_one_candidate_origin(self) -> None:
        self.assertEqual(
            MazeGenerator(7, 5)._candidate_origins(),
            [Coordinate(0, 0)],
        )
