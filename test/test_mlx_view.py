"""Tests for the MLX view lifecycle and drawing boundary."""

from unittest import TestCase

from maze import Maze
from maze_generator import GeneratedMaze
from maze_types import Coordinate
from mlx_view import MlxView


class FakeMlx:
    """Record MLX calls without requiring a graphical window."""

    SYNC_IMAGE_WRITABLE = 1

    def __init__(self, window: object = object()) -> None:
        self.window = window
        self.calls: list[tuple[str, object]] = []

    def mlx_init(self) -> object:
        self.calls.append(("init", None))
        return object()

    def mlx_new_window(
        self,
        _mlx_ptr: object,
        width: int,
        height: int,
        title: str,
    ) -> object:
        self.calls.append(("new_window", (width, height, title)))
        return self.window

    def mlx_release(self, _mlx_ptr: object) -> None:
        self.calls.append(("release", None))

    def mlx_loop_exit(self, _mlx_ptr: object) -> None:
        self.calls.append(("loop_exit", None))

    def mlx_destroy_window(
        self,
        _mlx_ptr: object,
        _window_ptr: object,
    ) -> None:
        self.calls.append(("destroy_window", None))

    def mlx_clear_window(
        self,
        _mlx_ptr: object,
        _window_ptr: object,
    ) -> None:
        self.calls.append(("clear_window", None))

    def mlx_pixel_put(
        self,
        _mlx_ptr: object,
        _window_ptr: object,
        _x: int,
        _y: int,
        _color: int,
    ) -> None:
        self.calls.append(("pixel_put", None))

    def mlx_string_put(
        self,
        _mlx_ptr: object,
        _window_ptr: object,
        _x: int,
        _y: int,
        _color: int,
        _text: str,
    ) -> None:
        self.calls.append(("string_put", _text))

    def mlx_sync(
        self,
        _mlx_ptr: object,
        _command: int,
        _image_ptr: object,
    ) -> None:
        self.calls.append(("sync_image", None))


def _result() -> GeneratedMaze:
    """Return a small generated-maze-shaped snapshot for view tests."""
    return GeneratedMaze(
        maze=Maze(2, 2),
        entry=Coordinate(0, 0),
        exit=Coordinate(1, 1),
        seed=42,
        pattern_omitted=True,
    )


class MlxViewTests(TestCase):
    """Verify MLX resources are created and released at explicit boundaries."""

    def test_cell_size_changes_at_display_boundaries(self) -> None:
        """Check the exact and just-over limits for a larger cell size."""
        cases = (
            ((576, 374), 2),
            ((577, 374), 1),
            ((576, 375), 1),
            ((1200, 800), 1),
        )
        for (width, height), expected in cases:
            with self.subTest(width=width, height=height):
                view = MlxView(width, height, mlx_factory=FakeMlx)
                self.assertEqual(view.cell_size, expected)
                self.assertEqual(
                    view.window_width,
                    width * expected
                    + view.HORIZONTAL_PADDING * 2,
                )
                self.assertEqual(
                    view.window_height,
                    height * expected
                    + view.VERTICAL_PADDING
                    + view.FOOTER_GAP
                    + view.FOOTER_HEIGHT,
                )

    def test_constructor_does_not_initialize_mlx(self) -> None:
        fake = FakeMlx()
        view = MlxView(2, 2, mlx_factory=lambda: fake)

        self.assertFalse(view.is_open)
        self.assertEqual(fake.calls, [])

    def test_open_draw_and_close_manage_resources(self) -> None:
        fake = FakeMlx()
        view = MlxView(2, 2, mlx_factory=lambda: fake)

        view.open()
        view.draw(_result())
        view.close()
        view.close()

        self.assertFalse(view.is_open)
        call_names = [name for name, _value in fake.calls]
        self.assertEqual(
            call_names[:2],
            ["init", "new_window"],
        )
        self.assertIn("clear_window", call_names)
        self.assertIn("pixel_put", call_names)
        self.assertIn("string_put", call_names)
        self.assertEqual(call_names[-2:], ["destroy_window", "release"])

    def test_context_manager_releases_resources(self) -> None:
        fake = FakeMlx()

        with MlxView(2, 2, mlx_factory=lambda: fake) as view:
            self.assertTrue(view.is_open)

        self.assertFalse(view.is_open)
        self.assertEqual(
            [name for name, _value in fake.calls][-2:],
            ["destroy_window", "release"],
        )

    def test_draw_requires_open_view(self) -> None:
        view = MlxView(2, 2, mlx_factory=FakeMlx)

        with self.assertRaises(RuntimeError):
            view.draw(_result())

    def test_dimensions_are_checked_before_drawing(self) -> None:
        fake = FakeMlx()
        view = MlxView(2, 2, mlx_factory=lambda: fake)
        view.open()

        with self.assertRaises(ValueError):
            view.draw(
                GeneratedMaze(
                    maze=Maze(3, 2),
                    entry=Coordinate(0, 0),
                    exit=Coordinate(2, 1),
                    seed=42,
                    pattern_omitted=True,
                )
            )

        view.close()

    def test_display_options_redraw_current_snapshot(self) -> None:
        fake = FakeMlx()
        view = MlxView(2, 2, mlx_factory=lambda: fake)
        result = _result()
        view.open()
        view.draw(result, "", show_solution=True)

        self.assertIs(view.current_result, result)
        self.assertEqual(view.current_solution, "")
        self.assertFalse(view.toggle_solution())
        first_wall_color = view.wall_color
        self.assertNotEqual(view.cycle_wall_color(), first_wall_color)
        self.assertTrue(view.handle_key("2"))
        self.assertTrue(view.show_solution)
        self.assertTrue(view.handle_key("3"))
        view.close()

    def test_numeric_shortcuts_control_the_view(self) -> None:
        """Use the visible 1-4 controls for view actions."""
        fake = FakeMlx()
        result = _result()
        replacement = GeneratedMaze(
            maze=Maze(2, 2),
            entry=Coordinate(0, 0),
            exit=Coordinate(1, 1),
            seed=99,
            pattern_omitted=True,
        )
        view = MlxView(2, 2, mlx_factory=lambda: fake)
        view.open()
        view.draw(result)
        view.set_regenerator(lambda: (replacement, ""))

        self.assertTrue(view.handle_key("1"))
        self.assertIs(view.current_result, replacement)
        self.assertTrue(view.handle_key("2"))
        self.assertFalse(view.show_solution)
        self.assertTrue(view.handle_key("3"))
        self.assertTrue(view.handle_key("4"))
        # The event loop is asked to exit; ``run`` owns final cleanup.
        self.assertTrue(view.is_open)
        view.close()

    def test_regeneration_replaces_only_after_success(self) -> None:
        fake = FakeMlx()
        result = _result()
        view = MlxView(2, 2, mlx_factory=lambda: fake)
        view.open()
        view.draw(result)

        replacement = GeneratedMaze(
            maze=Maze(2, 2),
            entry=Coordinate(0, 0),
            exit=Coordinate(1, 1),
            seed=99,
            pattern_omitted=True,
        )
        view.set_regenerator(lambda: (replacement, ""))
        self.assertTrue(view.handle_key("R"))
        self.assertIs(view.current_result, replacement)

        view.set_regenerator(lambda: (_raise_generation_error()))
        self.assertTrue(view.handle_key("r"))
        self.assertIs(view.current_result, replacement)
        view.close()


def _raise_generation_error() -> tuple[GeneratedMaze, str]:
    """Raise an error from a regeneration callback for failure tests."""
    raise RuntimeError("generation failed")
