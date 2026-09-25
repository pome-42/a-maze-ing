"""Tests for connecting configuration values to the maze model."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from config import Config, ConfigError
from maze_setup import create_maze_setup, load_maze_setup
from maze_types import ALL_WALLS, Coordinate


class MazeSetupTests(TestCase):
    """Test conversion from configuration to initial maze setup."""

    def test_create_maze_setup_connects_all_configuration_values(self) -> None:
        config = Config(
            width=4,
            height=3,
            entry=(0, 1),
            exit=(3, 2),
            output_file="maze.txt",
            perfect=True,
            seed=42,
        )

        setup = create_maze_setup(config)

        self.assertEqual(setup.maze.width, 4)
        self.assertEqual(setup.maze.height, 3)
        self.assertEqual(setup.entry, Coordinate(0, 1))
        self.assertEqual(setup.exit, Coordinate(3, 2))
        self.assertEqual(setup.output_file, "maze.txt")
        self.assertTrue(setup.perfect)
        self.assertEqual(setup.seed, 42)
        self.assertTrue(
            all(cell == ALL_WALLS for row in setup.maze.grid for cell in row)
        )

    def test_load_maze_setup_propagates_configuration_errors(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.txt"
            path.write_text("WIDTH=not-an-integer\n", encoding="utf-8")

            with self.assertRaises(ConfigError):
                load_maze_setup(str(path))

    def test_create_maze_setup_rejects_invalid_coordinates(self) -> None:
        config = Config(
            width=4,
            height=3,
            entry=(4, 0),
            exit=(3, 2),
            output_file="maze.txt",
            perfect=False,
        )

        with self.assertRaises(ValueError):
            create_maze_setup(config)
