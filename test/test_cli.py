"""Integration tests for the command-line entrypoint."""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = PROJECT_ROOT / "a_maze_ing.py"
VALID_CONFIG = """\
WIDTH=10
HEIGHT=8
ENTRY=0,0
EXIT=9,7
OUTPUT_FILE=maze.txt
PERFECT=True
SEED=42
"""


class CliTests(TestCase):
    """Verify CLI exit codes and user-facing output."""

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Run the CLI in the project root and capture both output streams."""
        return subprocess.run(
            [sys.executable, str(CLI_PATH), *arguments],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            check=False,
        )

    def test_valid_configuration_succeeds(self) -> None:
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.txt"
            config_path.write_text(VALID_CONFIG, encoding="utf-8")

            result = self.run_cli(str(config_path))

        self.assertEqual(result.returncode, 0)
        self.assertIn("Configuration loaded successfully.", result.stdout)
        self.assertIn("Maze size: 10 x 8", result.stdout)
        self.assertIn("Seed: 42", result.stdout)
        self.assertIn("Maze data initialized.", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_missing_argument_shows_usage_without_traceback(self) -> None:
        result = self.run_cli()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_extra_argument_shows_usage_without_traceback(self) -> None:
        result = self.run_cli("config.txt", "extra.txt")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_file_reports_configuration_error_without_traceback(
        self,
    ) -> None:
        result = self.run_cli("missing-config.txt")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("configuration error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_configuration_reports_configuration_error(self) -> None:
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "invalid.txt"
            config_path.write_text("WIDTH=not-an-integer\n", encoding="utf-8")

            result = self.run_cli(str(config_path))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("configuration error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
