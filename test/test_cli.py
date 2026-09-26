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
            output_path = Path(directory) / "maze.txt"
            config_path.write_text(
                VALID_CONFIG.replace("maze.txt", str(output_path)),
                encoding="utf-8",
            )

            result = self.run_cli(str(config_path))
            output_exists = output_path.exists()
            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0)
        self.assertIn("Configuration loaded successfully.", result.stdout)
        self.assertIn("Maze size: 10 x 8", result.stdout)
        self.assertIn("Seed: 42", result.stdout)
        self.assertIn("Maze data initialized.", result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertTrue(output_exists)
        self.assertTrue(output_text.endswith("\n"))
        output_lines = output_text.splitlines()
        self.assertEqual(len(output_lines), 12)
        self.assertEqual(output_lines[8], "")
        self.assertEqual(output_lines[9:11], ["0,0", "9,7"])
        self.assertRegex(output_lines[11], r"^[NESW]*$")

    def test_small_maze_warns_when_42_is_omitted(self) -> None:
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.txt"
            output_path = Path(directory) / "maze.txt"
            config_path.write_text(
                VALID_CONFIG.replace("WIDTH=10", "WIDTH=6")
                .replace("HEIGHT=8", "HEIGHT=4")
                .replace("EXIT=9,7", "EXIT=5,3")
                .replace("maze.txt", str(output_path)),
                encoding="utf-8",
            )

            result = self.run_cli(str(config_path))
            output_exists = output_path.exists()

        self.assertEqual(result.returncode, 0)
        self.assertIn("pattern omitted", result.stderr)
        self.assertTrue(output_exists)

    def test_non_perfect_configuration_succeeds(self) -> None:
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.txt"
            output_path = Path(directory) / "maze.txt"
            config_path.write_text(
                VALID_CONFIG.replace("PERFECT=True", "PERFECT=False")
                .replace("maze.txt", str(output_path)),
                encoding="utf-8",
            )

            result = self.run_cli(str(config_path))
            output_exists = output_path.exists()

        self.assertEqual(result.returncode, 0)
        self.assertIn("Perfect: False", result.stdout)
        self.assertIn("Seed: 42", result.stdout)
        self.assertTrue(output_exists)
        self.assertEqual(result.stderr, "")

    def test_non_perfect_small_size_reports_error(self) -> None:
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.txt"
            output_path = Path(directory) / "maze.txt"
            config_path.write_text(
                VALID_CONFIG.replace("WIDTH=10", "WIDTH=2")
                .replace("HEIGHT=8", "HEIGHT=2")
                .replace("EXIT=9,7", "EXIT=1,1")
                .replace("PERFECT=True", "PERFECT=False")
                .replace("maze.txt", str(output_path)),
                encoding="utf-8",
            )

            result = self.run_cli(str(config_path))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("generation error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_save_failure_is_reported_without_traceback(self) -> None:
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.txt"
            missing_parent = Path(directory) / "missing" / "maze.txt"
            config_path.write_text(
                VALID_CONFIG.replace("maze.txt", str(missing_parent)),
                encoding="utf-8",
            )

            result = self.run_cli(str(config_path))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("generation error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

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
