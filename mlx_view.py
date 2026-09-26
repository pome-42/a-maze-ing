"""Display generated mazes with the Linux MiniLibX wrapper."""

from collections.abc import Callable, Iterator
from importlib import import_module
import sys
from typing import Any, cast

from maze_generator import GeneratedMaze
from maze_types import Coordinate, Wall


MlxFactory = Callable[[], Any]
Regenerate = Callable[[], tuple[GeneratedMaze, str]]
_SOLUTION_STEPS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}


class MlxView:
    """Own an MLX window and draw immutable generated-maze snapshots."""

    MAX_WINDOW_WIDTH = 1200
    MAX_WINDOW_HEIGHT = 800
    HORIZONTAL_PADDING = 24
    VERTICAL_PADDING = 12
    FOOTER_GAP = 0
    FOOTER_HEIGHT = 40
    CONTROL_TEXT_HEIGHT = 16
    WALL_THICKNESS = 2
    OUTER_WALL_THICKNESS = WALL_THICKNESS * 2
    MARKER_PADDING = 1
    MARKER_RADIUS = 8
    OUTER_CORNER_RADIUS = 8
    MIN_CELL_SIZE = 1
    DEFAULT_TITLE = "A-Maze-ing"

    BACKGROUND_COLOR = 0x000000
    PASSAGE_COLOR = 0x505050
    WALL_COLOR = 0xFFFFFF
    ENTRY_COLOR = 0x00CC66
    EXIT_COLOR = 0xE04B4B
    PATTERN_COLOR = 0xD9A441
    PATH_COLOR = 0x4DA6FF
    PATH_THICKNESS = 8
    WALL_COLORS = (0xFFFFFF, 0xD9A441, 0x66CCFF)
    KEY_ESCAPE = 65307
    WINDOW_CLOSE_EVENT = 33

    def __init__(
        self,
        width: int,
        height: int,
        title: str = DEFAULT_TITLE,
        mlx_factory: MlxFactory | None = None,
        regenerate: Regenerate | None = None,
    ) -> None:
        """Prepare a view without creating an MLX resource."""
        if isinstance(width, bool) or not isinstance(width, int):
            raise TypeError("width must be an integer")
        if isinstance(height, bool) or not isinstance(height, int):
            raise TypeError("height must be an integer")
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be greater than 0")
        if not isinstance(title, str):
            raise TypeError("title must be a string")
        if not title:
            raise ValueError("title must not be empty")

        self.width = width
        self.height = height
        self.title = title
        self.cell_size = self._calculate_cell_size(width, height)
        self.window_width = (
            width * self.cell_size + self.HORIZONTAL_PADDING * 2
        )
        self.window_height = (
            height * self.cell_size
            + self.VERTICAL_PADDING
            + self.FOOTER_GAP
            + self.FOOTER_HEIGHT
        )
        self._mlx_factory = mlx_factory or self._default_mlx_factory
        self._mlx: Any | None = None
        self._mlx_ptr: Any | None = None
        self._window_ptr: Any | None = None
        self._image_ptr: Any | None = None
        self._image_data: memoryview | None = None
        self._image_stride = 0
        self._regenerate = regenerate
        self._current_result: GeneratedMaze | None = None
        self._current_solution = ""
        self._show_solution = True
        self._wall_color_index = 0

    @staticmethod
    def _calculate_cell_size(width: int, height: int) -> int:
        """Return a cell size that keeps the complete maze on screen."""
        return max(
            MlxView.MIN_CELL_SIZE,
            min(
                (
                    MlxView.MAX_WINDOW_WIDTH
                    - MlxView.HORIZONTAL_PADDING * 2
                )
                // width,
                (
                    MlxView.MAX_WINDOW_HEIGHT
                    - MlxView.VERTICAL_PADDING
                    - MlxView.FOOTER_GAP
                    - MlxView.FOOTER_HEIGHT
                )
                // height,
            ),
        )

    @staticmethod
    def _default_mlx_factory() -> Any:
        """Load MLX only when a view is opened."""
        try:
            mlx_module = import_module("mlx")
        except ImportError as error:
            raise RuntimeError(
                "MLX is not installed; install the Linux MLX wheel"
            ) from error
        return mlx_module.Mlx()

    @property
    def is_open(self) -> bool:
        """Return whether the view currently owns an MLX window."""
        return self._window_ptr is not None

    @property
    def show_solution(self) -> bool:
        """Return whether the current shortest path is visible."""
        return self._show_solution

    @property
    def wall_color(self) -> int:
        """Return the color currently used for closed walls."""
        return self.WALL_COLORS[self._wall_color_index]

    @property
    def current_result(self) -> GeneratedMaze | None:
        """Return the currently displayed generated-maze snapshot."""
        return self._current_result

    @property
    def current_solution(self) -> str:
        """Return the solution belonging to the displayed snapshot."""
        return self._current_solution

    def set_regenerator(self, regenerate: Regenerate | None) -> None:
        """Set or clear the callback used by the ``R`` key."""
        if regenerate is not None and not callable(regenerate):
            raise TypeError("regenerate must be callable or None")
        self._regenerate = regenerate

    def open(self) -> None:
        """Initialize MLX and create the view window."""
        if self.is_open:
            raise RuntimeError("MLX view is already open")

        mlx = self._mlx_factory()
        mlx_ptr = mlx.mlx_init()
        if not mlx_ptr:
            raise RuntimeError("failed to initialize MLX")

        try:
            window_ptr = mlx.mlx_new_window(
                mlx_ptr,
                self.window_width,
                self.window_height,
                self.title,
            )
            if not window_ptr:
                raise RuntimeError("failed to create MLX window")
        except Exception:
            mlx.mlx_release(mlx_ptr)
            raise

        self._mlx = mlx
        self._mlx_ptr = mlx_ptr
        self._window_ptr = window_ptr

    def close(self) -> None:
        """Destroy the window and release MLX resources, if open."""
        mlx = self._mlx
        mlx_ptr = self._mlx_ptr
        window_ptr = self._window_ptr
        image_ptr = self._image_ptr
        self._mlx = None
        self._mlx_ptr = None
        self._window_ptr = None
        self._image_ptr = None
        self._image_data = None
        self._image_stride = 0

        if mlx is None or mlx_ptr is None:
            return

        try:
            if image_ptr is not None:
                mlx.mlx_destroy_image(mlx_ptr, image_ptr)
            if window_ptr is not None:
                mlx.mlx_destroy_window(mlx_ptr, window_ptr)
        finally:
            mlx.mlx_release(mlx_ptr)

    def __enter__(self) -> "MlxView":
        """Open and return this view for use in a with statement."""
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        """Release MLX resources at the end of a with statement."""
        self.close()

    def draw(
        self,
        result: GeneratedMaze,
        solution: str = "",
        show_solution: bool = True,
    ) -> None:
        """Draw a generated maze snapshot and an optional solution path."""
        self._require_open()
        if not isinstance(result, GeneratedMaze):
            raise TypeError("result must be a GeneratedMaze")
        dimensions_match = (
            result.maze.width == self.width
            and result.maze.height == self.height
        )
        if not dimensions_match:
            raise ValueError("generated maze dimensions do not match the view")
        if not isinstance(solution, str):
            raise TypeError("solution must be a string")
        if any(
            direction not in _SOLUTION_STEPS
            for direction in solution
        ):
            raise ValueError("solution contains an invalid direction")
        if not isinstance(show_solution, bool):
            raise TypeError("show_solution must be a boolean")

        assert self._mlx is not None
        assert self._mlx_ptr is not None
        assert self._window_ptr is not None
        using_image = self._ensure_image()
        if using_image:
            self._sync_image_for_writing()
        if using_image:
            self._fill_rect(
                0,
                0,
                self.window_width,
                self.window_height,
                self.BACKGROUND_COLOR,
            )
        else:
            self._mlx.mlx_clear_window(self._mlx_ptr, self._window_ptr)

        for y, row in enumerate(result.grid):
            for x, walls in enumerate(row):
                position = Coordinate(x, y)
                if position in result.pattern_cells:
                    left = self.HORIZONTAL_PADDING + x * self.cell_size
                    top = self.VERTICAL_PADDING + y * self.cell_size
                    self._fill_rect(
                        left,
                        top,
                        self.cell_size,
                        self.cell_size,
                        self.PATTERN_COLOR,
                    )

        if show_solution:
            self._draw_path(result.entry, solution)

        for y, row in enumerate(result.grid):
            for x, walls in enumerate(row):
                position = Coordinate(x, y)
                left = (
                    self.HORIZONTAL_PADDING
                    + x * self.cell_size
                )
                top = self.VERTICAL_PADDING + y * self.cell_size
                if position == result.entry:
                    self._fill_marker(
                        left,
                        top,
                        self.cell_size,
                        self.cell_size,
                        self.ENTRY_COLOR,
                        walls,
                    )
                elif position == result.exit:
                    self._fill_marker(
                        left,
                        top,
                        self.cell_size,
                        self.cell_size,
                        self.EXIT_COLOR,
                        walls,
                    )
                self._draw_walls(left, top, walls)

        self._draw_footer_background()
        if using_image:
            assert self._image_ptr is not None
            self._mlx.mlx_put_image_to_window(
                self._mlx_ptr,
                self._window_ptr,
                self._image_ptr,
                0,
                0,
            )
        self._draw_controls()
        sync = getattr(self._mlx, "mlx_do_sync", None)
        if sync is not None:
            sync(self._mlx_ptr)
        detailed_sync = getattr(self._mlx, "mlx_sync", None)
        flush_mode = getattr(self._mlx, "SYNC_WIN_FLUSH", None)
        if callable(detailed_sync) and flush_mode is not None:
            detailed_sync(self._mlx_ptr, flush_mode, self._window_ptr)
        self._current_result = result
        self._current_solution = solution
        self._show_solution = show_solution

    def toggle_solution(self) -> bool:
        """Toggle the shortest path and redraw the current maze.

        Return the new visibility state.  The view must already be open and
        have a maze displayed.
        """
        self._require_open()
        if self._current_result is None:
            raise RuntimeError("no generated maze is displayed")
        self._show_solution = not self._show_solution
        self._redraw_current()
        return self._show_solution

    def cycle_wall_color(self) -> int:
        """Select the next wall color and redraw the current maze."""
        self._require_open()
        self._wall_color_index = (
            self._wall_color_index + 1
        ) % len(self.WALL_COLORS)
        if self._current_result is not None:
            self._redraw_current()
        return self.wall_color

    def handle_key(self, keycode: int | str) -> bool:
        """Handle one MLX key code and return whether it was recognized."""
        key: str | None
        if isinstance(keycode, str):
            if len(keycode) != 1:
                raise ValueError("keycode string must contain one character")
            key = {
                "1": "r",
                "2": "p",
                "3": "c",
                "4": "escape",
            }.get(keycode, keycode.lower())
        elif isinstance(keycode, int) and not isinstance(keycode, bool):
            key = {
                ord("1"): "r",
                ord("2"): "p",
                ord("3"): "c",
                ord("4"): "escape",
                self.KEY_ESCAPE: "escape",
            }.get(keycode)
        else:
            raise TypeError(
                "keycode must be an integer or one-character string"
            )

        if key == "escape":
            if self._mlx is not None and self._mlx_ptr is not None:
                self._mlx.mlx_loop_exit(self._mlx_ptr)
            self.close()
            return True
        if key == "p":
            self.toggle_solution()
            return True
        if key == "c":
            self.cycle_wall_color()
            return True
        if key == "r":
            self.regenerate()
            return True
        return False

    def regenerate(self) -> bool:
        """Generate and display a new maze through the configured callback.

        The current display remains intact when generation or drawing fails.
        Return ``True`` after a successful replacement and ``False`` when no
        callback is configured.
        """
        self._require_open()
        if self._regenerate is None:
            return False
        try:
            result, solution = self._regenerate()
            self.draw(result, solution, self._show_solution)
        except Exception as error:
            print(f"maze regeneration failed: {error}", file=sys.stderr)
            return False
        return True

    def run(
        self,
        result: GeneratedMaze,
        solution: str = "",
    ) -> None:
        """Open the window, display a maze, process events, and close it."""
        self.open()
        try:
            self.draw(result, solution)
            assert self._mlx is not None
            assert self._mlx_ptr is not None
            assert self._window_ptr is not None
            self._mlx.mlx_key_hook(
                self._window_ptr,
                self._key_callback,
                None,
            )
            self._mlx.mlx_hook(
                self._window_ptr,
                self.WINDOW_CLOSE_EVENT,
                0,
                self._close_callback,
                None,
            )
            self._mlx.mlx_expose_hook(
                self._window_ptr,
                self._expose_callback,
                None,
            )
            self._mlx.mlx_loop(self._mlx_ptr)
        finally:
            self.close()

    def _key_callback(self, keycode: int, _param: object) -> None:
        """Adapt MLX's key callback to the public key handler."""
        try:
            self.handle_key(keycode)
        except Exception as error:
            print(f"MLX key handling failed: {error}", file=sys.stderr)

    def _close_callback(self, _param: object) -> None:
        """Exit MLX's event loop after a window close request."""
        if self._mlx is not None and self._mlx_ptr is not None:
            self._mlx.mlx_loop_exit(self._mlx_ptr)

    def _expose_callback(self, _param: object) -> None:
        """Redraw the current snapshot after the window is exposed."""
        if self._current_result is None or not self.is_open:
            return
        try:
            self._redraw_current()
        except Exception as error:
            print(f"MLX redraw failed: {error}", file=sys.stderr)

    def _redraw_current(self) -> None:
        """Redraw the stored snapshot with the current display options."""
        if self._current_result is None:
            raise RuntimeError("no generated maze is displayed")
        result = self._current_result
        solution = self._current_solution
        self.draw(result, solution, self._show_solution)

    def _require_open(self) -> None:
        """Raise when drawing is attempted without an owned window."""
        if not self.is_open:
            raise RuntimeError("MLX view is not open")

    def _fill_rect(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
        color: int,
    ) -> None:
        """Fill a rectangle using MLX's pixel primitive."""
        for y in range(top, top + height):
            for x in range(left, left + width):
                self._put_pixel(x, y, color)

    def _ensure_image(self) -> bool:
        """Create the off-screen image when the MLX wrapper supports it."""
        assert self._mlx is not None
        assert self._mlx_ptr is not None
        if self._image_ptr is not None:
            return True

        new_image = getattr(self._mlx, "mlx_new_image", None)
        get_data_addr = getattr(self._mlx, "mlx_get_data_addr", None)
        put_image = getattr(self._mlx, "mlx_put_image_to_window", None)
        if (
            not callable(new_image)
            or not callable(get_data_addr)
            or not callable(put_image)
        ):
            return False
        new_image_fn = cast(Callable[..., Any], new_image)
        get_data_addr_fn = cast(Callable[..., Any], get_data_addr)

        image_ptr = new_image_fn(
            self._mlx_ptr,
            self.window_width,
            self.window_height,
        )
        if not image_ptr:
            raise RuntimeError("failed to create MLX image")
        try:
            image_data, bits_per_pixel, stride, _format = get_data_addr_fn(
                image_ptr
            )
            if bits_per_pixel != 32 or stride < self.window_width * 4:
                raise RuntimeError("MLX image does not use 32-bit pixels")
        except Exception:
            self._mlx.mlx_destroy_image(self._mlx_ptr, image_ptr)
            raise

        self._image_ptr = image_ptr
        self._image_data = image_data
        self._image_stride = stride
        return True

    def _sync_image_for_writing(self) -> None:
        """Acquire the MLX image buffer before writing pixels into it."""
        assert self._mlx is not None
        assert self._mlx_ptr is not None
        assert self._image_ptr is not None
        sync = getattr(self._mlx, "mlx_sync", None)
        sync_mode = getattr(self._mlx, "SYNC_IMAGE_WRITABLE", None)
        if callable(sync) and sync_mode is not None:
            sync(self._mlx_ptr, sync_mode, self._image_ptr)

    def _put_pixel(self, x: int, y: int, color: int) -> None:
        """Write one pixel to the image buffer or directly to the window."""
        assert self._mlx is not None
        assert self._mlx_ptr is not None
        assert self._window_ptr is not None
        if self._image_data is not None:
            offset = y * self._image_stride + x * 4
            opaque_color = color | 0xFF000000
            self._image_data[offset:offset + 4] = opaque_color.to_bytes(
                4,
                "little",
            )
            return
        self._mlx.mlx_pixel_put(
            self._mlx_ptr,
            self._window_ptr,
            x,
            y,
            color,
        )

    def _draw_footer_background(self) -> None:
        """Draw the background reserved for the keyboard controls."""
        footer_top = (
            self.VERTICAL_PADDING
            + self.height * self.cell_size
            + self.FOOTER_GAP
        )
        self._fill_rect(
            self.HORIZONTAL_PADDING,
            footer_top,
            self.window_width - self.HORIZONTAL_PADDING * 2,
            self.FOOTER_HEIGHT,
            self.BACKGROUND_COLOR,
        )

    def _fill_marker(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
        color: int,
        walls: Wall,
    ) -> None:
        """Draw a cell marker with a small inset and rounded corners."""
        base_padding = min(
            self.MARKER_PADDING,
            max((width - 1) // 2, 0),
            max((height - 1) // 2, 0),
        )
        thickness = min(self.OUTER_WALL_THICKNESS, width, height)
        left_padding = base_padding + (
            thickness if walls & Wall.WEST else 0
        )
        right_padding = base_padding + (
            thickness if walls & Wall.EAST else 0
        )
        top_padding = base_padding + (
            thickness if walls & Wall.NORTH else 0
        )
        bottom_padding = base_padding + (
            thickness if walls & Wall.SOUTH else 0
        )
        if left_padding + right_padding >= width:
            left_padding = right_padding = max((width - 1) // 2, 0)
        if top_padding + bottom_padding >= height:
            top_padding = bottom_padding = max((height - 1) // 2, 0)

        marker_left = left + left_padding
        marker_top = top + top_padding
        marker_width = width - left_padding - right_padding
        marker_height = height - top_padding - bottom_padding
        radius = min(
            self.MARKER_RADIUS,
            marker_width // 2,
            marker_height // 2,
        )

        for y in range(marker_height):
            for x in range(marker_width):
                if radius and not self._inside_rounded_corner(
                    x,
                    y,
                    marker_width,
                    marker_height,
                    radius,
                ):
                    continue
                self._put_pixel(
                    marker_left + x,
                    marker_top + y,
                    color,
                )

    def _draw_path(self, entry: Coordinate, solution: str) -> None:
        """Draw the solution as a line through cell centers."""
        current = entry
        self._draw_path_joint(current)
        for direction in solution:
            dx, dy = _SOLUTION_STEPS[direction]
            next_position = Coordinate(
                current.x + dx,
                current.y + dy,
            )
            self._draw_path_segment(current, next_position)
            self._draw_path_joint(next_position)
            current = next_position

    def _draw_path_joint(self, position: Coordinate) -> None:
        """Draw a round joint at a path cell center."""
        thickness = min(self.PATH_THICKNESS, self.cell_size)
        radius = thickness // 2
        center_x = (
            self.HORIZONTAL_PADDING
            + position.x * self.cell_size
            + self.cell_size // 2
        )
        center_y = (
            self.VERTICAL_PADDING
            + position.y * self.cell_size
            + self.cell_size // 2
        )
        for y in range(center_y - radius, center_y + radius):
            for x in range(center_x - radius, center_x + radius):
                dx = x - center_x
                dy = y - center_y
                if dx * dx + dy * dy < radius * radius:
                    self._put_pixel(x, y, self.PATH_COLOR)

    def _draw_path_segment(
        self,
        start: Coordinate,
        end: Coordinate,
    ) -> None:
        """Draw one four-pixel-wide cardinal path segment."""
        thickness = min(self.PATH_THICKNESS, self.cell_size)
        start_x = self.HORIZONTAL_PADDING + start.x * self.cell_size
        start_y = self.VERTICAL_PADDING + start.y * self.cell_size
        end_x = self.HORIZONTAL_PADDING + end.x * self.cell_size
        end_y = self.VERTICAL_PADDING + end.y * self.cell_size
        start_x += self.cell_size // 2
        start_y += self.cell_size // 2
        end_x += self.cell_size // 2
        end_y += self.cell_size // 2

        if start_y == end_y:
            left = min(start_x, end_x)
            right = max(start_x, end_x)
            for y in range(
                start_y - thickness // 2,
                start_y - thickness // 2 + thickness,
            ):
                for x in range(left, right + 1):
                    self._put_pixel(x, y, self.PATH_COLOR)
            return

        top = min(start_y, end_y)
        bottom = max(start_y, end_y)
        for y in range(top, bottom + 1):
            for x in range(
                start_x - thickness // 2,
                start_x - thickness // 2 + thickness,
            ):
                self._put_pixel(x, y, self.PATH_COLOR)

    @staticmethod
    def _inside_rounded_corner(
        x: int,
        y: int,
        width: int,
        height: int,
        radius: int,
    ) -> bool:
        """Return whether a pixel belongs to a rounded rectangle."""
        corner_x = radius - 1 if x < radius else width - radius
        corner_y = radius - 1 if y < radius else height - radius
        if x < radius or x >= width - radius:
            if y < radius or y >= height - radius:
                dx = x - corner_x
                dy = y - corner_y
                return dx * dx + dy * dy < radius * radius
        return True

    def _draw_controls(self) -> None:
        """Draw keyboard controls below the maze."""
        assert self._mlx is not None
        assert self._mlx_ptr is not None
        assert self._window_ptr is not None
        string_put = getattr(self._mlx, "mlx_string_put", None)
        if not callable(string_put):
            return

        footer_top = (
            self.VERTICAL_PADDING
            + self.height * self.cell_size
            + self.FOOTER_GAP
        )
        string_put(
            self._mlx_ptr,
            self._window_ptr,
            self.HORIZONTAL_PADDING + 8,
            footer_top
            + (self.FOOTER_HEIGHT - self.CONTROL_TEXT_HEIGHT) // 2,
            self.WALL_COLOR,
            "1: Regen    2: Path    3: Color    4: Quit",
        )

    def _draw_walls(self, left: int, top: int, walls: Wall) -> None:
        """Draw the closed walls around one cell."""
        if walls & Wall.NORTH:
            outer = top == self.VERTICAL_PADDING
            thickness = self._wall_thickness(outer)
            self._draw_horizontal_line(left, top, thickness, outer)
        if walls & Wall.SOUTH:
            bottom = top + self.cell_size
            outer = (
                bottom
                == self.VERTICAL_PADDING + self.height * self.cell_size
            )
            thickness = self._wall_thickness(outer)
            self._draw_horizontal_line(
                left,
                bottom - thickness,
                thickness,
                outer,
            )
        if walls & Wall.WEST:
            outer = left == self.HORIZONTAL_PADDING
            thickness = self._wall_thickness(outer)
            self._draw_vertical_line(left, top, thickness, outer)
        if walls & Wall.EAST:
            right = left + self.cell_size
            outer = (
                right
                == self.HORIZONTAL_PADDING + self.width * self.cell_size
            )
            thickness = self._wall_thickness(outer)
            self._draw_vertical_line(
                right - thickness,
                top,
                thickness,
                outer,
            )

    def _wall_thickness(self, outer: bool) -> int:
        """Return the pixel thickness used for an outer or inner wall."""
        thickness = (
            self.OUTER_WALL_THICKNESS if outer else self.WALL_THICKNESS
        )
        return min(thickness, self.cell_size)

    def _draw_horizontal_line(
        self,
        left: int,
        top: int,
        thickness: int,
        outer: bool,
    ) -> None:
        """Draw one horizontal wall segment."""
        for y in range(top, top + thickness):
            for x in range(left, left + self.cell_size):
                if outer and not self._inside_outer_corner(x, y):
                    continue
                self._put_pixel(x, y, self.wall_color)

    def _draw_vertical_line(
        self,
        left: int,
        top: int,
        thickness: int,
        outer: bool,
    ) -> None:
        """Draw one vertical wall segment."""
        for x in range(left, left + thickness):
            for y in range(top, top + self.cell_size):
                if outer and not self._inside_outer_corner(x, y):
                    continue
                self._put_pixel(x, y, self.wall_color)

    def _inside_outer_corner(self, x: int, y: int) -> bool:
        """Return whether a pixel belongs to the rounded maze outline."""
        maze_left = self.HORIZONTAL_PADDING
        maze_top = self.VERTICAL_PADDING
        maze_width = self.width * self.cell_size
        maze_height = self.height * self.cell_size
        radius = min(
            self.OUTER_CORNER_RADIUS,
            maze_width // 2,
            maze_height // 2,
        )
        return self._inside_rounded_corner(
            x - maze_left,
            y - maze_top,
            maze_width,
            maze_height,
            radius,
        )

    @staticmethod
    def _solution_cells(
        entry: Coordinate,
        solution: str,
    ) -> set[Coordinate]:
        """Return the cells visited by a direction-string solution."""
        cells = {entry}
        current = entry
        for direction in solution:
            dx, dy = _SOLUTION_STEPS[direction]
            current = Coordinate(current.x + dx, current.y + dy)
            cells.add(current)
        return cells


def iter_solution_cells(
    entry: Coordinate,
    solution: str,
) -> Iterator[Coordinate]:
    """Yield each cell visited by a direction-string solution."""
    current = entry
    yield current
    for direction in solution:
        dx, dy = _SOLUTION_STEPS[direction]
        current = Coordinate(current.x + dx, current.y + dy)
        yield current
