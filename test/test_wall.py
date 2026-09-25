"""Tests for wall bit flags."""

from unittest import TestCase

from maze_types import ALL_WALLS, Wall


class WallTests(TestCase):
    """Test wall bit flag behavior."""

    def test_wall_values(self) -> None:
        self.assertEqual(Wall.NORTH.value, 1)
        self.assertEqual(Wall.EAST.value, 2)
        self.assertEqual(Wall.SOUTH.value, 4)
        self.assertEqual(Wall.WEST.value, 8)

    def test_all_walls_contains_every_direction(self) -> None:
        self.assertEqual(int(ALL_WALLS), 15)
        self.assertTrue(ALL_WALLS & Wall.NORTH)
        self.assertTrue(ALL_WALLS & Wall.EAST)
        self.assertTrue(ALL_WALLS & Wall.SOUTH)
        self.assertTrue(ALL_WALLS & Wall.WEST)

    def test_wall_can_be_opened_by_clearing_a_bit(self) -> None:
        walls = ALL_WALLS & ~Wall.EAST

        self.assertFalse(walls & Wall.EAST)
        self.assertTrue(walls & Wall.NORTH)
        self.assertTrue(walls & Wall.SOUTH)
        self.assertTrue(walls & Wall.WEST)
