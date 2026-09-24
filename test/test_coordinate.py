"""Tests for the Coordinate value object."""

from dataclasses import FrozenInstanceError
from unittest import TestCase

from maze_types import Coordinate


class CoordinateTests(TestCase):
    """Test Coordinate behavior."""

    def test_create_coordinate(self) -> None:
        position = Coordinate(4, 2)

        self.assertEqual(position.x, 4)
        self.assertEqual(position.y, 2)

    def test_convert_coordinate_to_tuple(self) -> None:
        position = Coordinate(4, 2)

        result = position.as_tuple()

        self.assertEqual(result, (4, 2))

    def test_reject_non_integer_coordinate(self) -> None:
        with self.assertRaises(TypeError):
            Coordinate(1.5, 2)

        with self.assertRaises(TypeError):
            Coordinate(1, "2")

        with self.assertRaises(TypeError):
            Coordinate(True, 2)

        with self.assertRaises(TypeError):
            Coordinate(1, False)

    def test_coordinate_is_immutable(self) -> None:
        position = Coordinate(4, 2)

        with self.assertRaises(FrozenInstanceError):
            position.x = 5
