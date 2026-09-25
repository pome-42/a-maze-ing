"""Independent validation of maze grid and wall invariants."""

from dataclasses import dataclass

from maze_types import ALL_WALLS, Coordinate, Wall


@dataclass(frozen=True)
class MazeValidationInput:
    """Snapshot and metadata supplied to the independent validator."""

    grid: tuple[tuple[Wall, ...], ...]
    width: int
    height: int
    entry: Coordinate
    exit: Coordinate
    pattern_cells: frozenset[Coordinate]
    perfect: bool


@dataclass(frozen=True)
class ValidationReport:
    """Collect validation errors without changing the input snapshot."""

    errors: tuple[str, ...]
    vertex_count: int = 0
    edge_count: int = 0

    @property
    def is_valid(self) -> bool:
        """Return whether no validation errors were found."""
        return not self.errors


def validate_maze(data: MazeValidationInput) -> ValidationReport:
    """Validate basic grid, wall, coordinate, and reservation invariants."""
    if not isinstance(data, MazeValidationInput):
        raise TypeError("data must be a MazeValidationInput")

    errors: list[str] = []
    vertex_count = 0
    edge_count = 0
    dimensions_valid = _validate_dimensions(data, errors)
    shape_valid = dimensions_valid and _validate_grid_shape(data, errors)
    cells_valid = shape_valid and _validate_cell_values(data, errors)

    _validate_coordinates(data, errors, dimensions_valid)
    pattern_shape_valid = dimensions_valid and _validate_pattern_cells(
        data,
        errors,
    )

    if shape_valid and cells_valid:
        _validate_outer_walls(data, errors)
        _validate_adjacent_walls(data, errors)

    if pattern_shape_valid and cells_valid:
        _validate_reserved_cells(data, errors)
        vertex_count, edge_count = _validate_passage_graph(data, errors)

    return ValidationReport(tuple(errors), vertex_count, edge_count)


def _validate_dimensions(
    data: MazeValidationInput,
    errors: list[str],
) -> bool:
    """Validate the declared positive integer dimensions."""
    valid = True
    for name, value in (("width", data.width), ("height", data.height)):
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{name} must be an integer")
            valid = False
        elif value <= 0:
            errors.append(f"{name} must be greater than 0")
            valid = False
    return valid


def _validate_grid_shape(
    data: MazeValidationInput,
    errors: list[str],
) -> bool:
    """Validate that the grid has the declared rectangular dimensions."""
    if not isinstance(data.grid, tuple):
        errors.append("grid must be a tuple of rows")
        return False
    if len(data.grid) != data.height:
        errors.append(
            f"grid must have {data.height} rows, got {len(data.grid)}"
        )
    valid = len(data.grid) == data.height
    for row_index, row in enumerate(data.grid):
        if not isinstance(row, tuple):
            errors.append(f"grid row {row_index} must be a tuple")
            valid = False
            continue
        if len(row) != data.width:
            errors.append(
                f"grid row {row_index} must have {data.width} cells, "
                f"got {len(row)}"
            )
            valid = False
    return valid


def _validate_cell_values(
    data: MazeValidationInput,
    errors: list[str],
) -> bool:
    """Validate that every cell is a four-bit Wall value."""
    valid = True
    for y, row in enumerate(data.grid):
        if not isinstance(row, tuple):
            continue
        for x, cell in enumerate(row):
            if isinstance(cell, bool) or not isinstance(cell, Wall):
                errors.append(f"cell ({x}, {y}) must be a Wall value")
                valid = False
            elif int(cell) < 0 or int(cell) > int(ALL_WALLS):
                errors.append(f"cell ({x}, {y}) has an invalid wall value")
                valid = False
    return valid


def _validate_coordinates(
    data: MazeValidationInput,
    errors: list[str],
    dimensions_valid: bool,
) -> None:
    """Validate entry and exit coordinate types and bounds."""
    for name, position in (("entry", data.entry), ("exit", data.exit)):
        if not isinstance(position, Coordinate):
            errors.append(f"{name} must be a Coordinate")
            continue
        if dimensions_valid and not _in_bounds(
            position,
            data.width,
            data.height,
        ):
            errors.append(f"{name} is outside the maze bounds")
    if (
        isinstance(data.entry, Coordinate)
        and isinstance(data.exit, Coordinate)
        and data.entry == data.exit
    ):
        errors.append("entry and exit must be different")


def _validate_pattern_cells(
    data: MazeValidationInput,
    errors: list[str],
) -> bool:
    """Validate the reservation collection's type and coordinate values."""
    if not isinstance(data.pattern_cells, frozenset):
        errors.append("pattern_cells must be a frozenset")
        return False
    valid = True
    for position in data.pattern_cells:
        if not isinstance(position, Coordinate):
            errors.append("pattern_cells must contain Coordinates")
            valid = False
        elif not _in_bounds(position, data.width, data.height):
            errors.append(
                f"pattern cell ({position.x}, {position.y}) is out of bounds"
            )
            valid = False
    return valid


def _validate_outer_walls(
    data: MazeValidationInput,
    errors: list[str],
) -> None:
    """Ensure every outer boundary wall remains closed."""
    for y, row in enumerate(data.grid):
        for x, walls in enumerate(row):
            if y == 0 and not walls & Wall.NORTH:
                errors.append(f"outer NORTH wall is open at ({x}, {y})")
            if x == data.width - 1 and not walls & Wall.EAST:
                errors.append(f"outer EAST wall is open at ({x}, {y})")
            if y == data.height - 1 and not walls & Wall.SOUTH:
                errors.append(f"outer SOUTH wall is open at ({x}, {y})")
            if x == 0 and not walls & Wall.WEST:
                errors.append(f"outer WEST wall is open at ({x}, {y})")


def _validate_adjacent_walls(
    data: MazeValidationInput,
    errors: list[str],
) -> None:
    """Ensure shared walls have matching closed/open states."""
    for y, row in enumerate(data.grid):
        for x, walls in enumerate(row):
            if x + 1 < data.width:
                east = data.grid[y][x + 1]
                if bool(walls & Wall.EAST) != bool(east & Wall.WEST):
                    errors.append(
                        f"east/west walls disagree between ({x}, {y}) and "
                        f"({x + 1}, {y})"
                    )
            if y + 1 < data.height:
                south = data.grid[y + 1][x]
                if bool(walls & Wall.SOUTH) != bool(south & Wall.NORTH):
                    errors.append(
                        f"south/north walls disagree between ({x}, {y}) and "
                        f"({x}, {y + 1})"
                    )


def _validate_reserved_cells(
    data: MazeValidationInput,
    errors: list[str],
) -> None:
    """Ensure reserved cells are closed and are not entry or exit cells."""
    for position in data.pattern_cells:
        if position == data.entry or position == data.exit:
            errors.append(
                f"pattern cell ({position.x}, {position.y}) overlaps entry "
                "or exit"
            )
        if data.grid[position.y][position.x] != ALL_WALLS:
            errors.append(
                f"pattern cell ({position.x}, {position.y}) is not fully "
                "closed"
            )


def _validate_passage_graph(
    data: MazeValidationInput,
    errors: list[str],
) -> tuple[int, int]:
    """Validate passage reachability and reject fully open 3x3 areas."""
    if not _valid_playable_coordinate(data.entry, data) or not (
        _valid_playable_coordinate(data.exit, data)
    ):
        return 0, 0

    vertices = {
        Coordinate(x, y)
        for y in range(data.height)
        for x in range(data.width)
        if Coordinate(x, y) not in data.pattern_cells
    }
    if data.entry not in vertices:
        errors.append("entry must be a non-reserved passage cell")
        return len(vertices), 0
    if data.exit not in vertices:
        errors.append("exit must be a non-reserved passage cell")
        return len(vertices), 0

    adjacency: dict[Coordinate, set[Coordinate]] = {
        position: set() for position in vertices
    }
    edge_count = 0
    for y in range(data.height):
        for x in range(data.width):
            position = Coordinate(x, y)
            if position not in vertices:
                continue
            if x + 1 < data.width:
                neighbour = Coordinate(x + 1, y)
                if neighbour in vertices and _is_open_east(data, x, y):
                    adjacency[position].add(neighbour)
                    adjacency[neighbour].add(position)
                    edge_count += 1
            if y + 1 < data.height:
                neighbour = Coordinate(x, y + 1)
                if neighbour in vertices and _is_open_south(data, x, y):
                    adjacency[position].add(neighbour)
                    adjacency[neighbour].add(position)
                    edge_count += 1

    reachable = _reachable_from(data.entry, adjacency)
    unreachable = sorted(vertices - reachable, key=lambda p: (p.y, p.x))
    for position in unreachable:
        errors.append(
            f"passage cell ({position.x}, {position.y}) is unreachable"
        )

    if data.exit not in reachable:
        errors.append("exit is unreachable from entry")

    _validate_open_3x3_areas(data, errors)
    return len(vertices), edge_count


def _valid_playable_coordinate(
    position: object,
    data: MazeValidationInput,
) -> bool:
    """Return whether a coordinate is typed and inside the grid."""
    return (
        isinstance(position, Coordinate)
        and _in_bounds(position, data.width, data.height)
    )


def _is_open_east(data: MazeValidationInput, x: int, y: int) -> bool:
    """Return whether the east/west shared wall is open."""
    return not (
        data.grid[y][x] & Wall.EAST
        or data.grid[y][x + 1] & Wall.WEST
    )


def _is_open_south(data: MazeValidationInput, x: int, y: int) -> bool:
    """Return whether the south/north shared wall is open."""
    return not (
        data.grid[y][x] & Wall.SOUTH
        or data.grid[y + 1][x] & Wall.NORTH
    )


def _reachable_from(
    start: Coordinate,
    adjacency: dict[Coordinate, set[Coordinate]],
) -> set[Coordinate]:
    """Return the vertices reachable from a graph start vertex."""
    reachable = {start}
    pending = [start]
    while pending:
        current = pending.pop()
        for neighbour in adjacency[current]:
            if neighbour not in reachable:
                reachable.add(neighbour)
                pending.append(neighbour)
    return reachable


def _validate_open_3x3_areas(
    data: MazeValidationInput,
    errors: list[str],
) -> None:
    """Reject a 3x3 area whose twelve internal edges are all open."""
    for y in range(data.height - 2):
        for x in range(data.width - 2):
            all_open = all(
                _is_open_east(data, cell_x, cell_y)
                for cell_y in range(y, y + 3)
                for cell_x in range(x, x + 2)
            ) and all(
                _is_open_south(data, cell_x, cell_y)
                for cell_y in range(y, y + 2)
                for cell_x in range(x, x + 3)
            )
            if all_open:
                errors.append(
                    f"3x3 fully open area starts at ({x}, {y})"
                )


def _in_bounds(position: Coordinate, width: int, height: int) -> bool:
    """Return whether a coordinate is inside the declared dimensions."""
    return 0 <= position.x < width and 0 <= position.y < height
