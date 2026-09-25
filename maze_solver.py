"""Find shortest paths through generated maze grids."""

from collections import deque

from maze import Maze
from maze_types import Coordinate, Wall


def shortest_path(
    maze: Maze,
    entry: Coordinate,
    exit: Coordinate,
) -> str:
    """Return the shortest path from entry to exit as NESW characters."""
    if not isinstance(maze, Maze):
        raise TypeError("maze must be a Maze")
    if not isinstance(entry, Coordinate):
        raise TypeError("entry must be a Coordinate")
    if not isinstance(exit, Coordinate):
        raise TypeError("exit must be a Coordinate")
    if not maze.in_bounds(entry):
        raise ValueError("entry must be inside the maze bounds")
    if not maze.in_bounds(exit):
        raise ValueError("exit must be inside the maze bounds")
    if entry == exit:
        return ""

    directions = (
        (Wall.NORTH, "N", 0, -1),
        (Wall.EAST, "E", 1, 0),
        (Wall.SOUTH, "S", 0, 1),
        (Wall.WEST, "W", -1, 0),
    )
    queue = deque([entry])
    previous: dict[Coordinate, tuple[Coordinate, str] | None] = {
        entry: None
    }

    while queue:
        current = queue.popleft()
        for wall, symbol, dx, dy in directions:
            if maze.get_walls(current) & wall:
                continue
            neighbour = Coordinate(current.x + dx, current.y + dy)
            if not maze.in_bounds(neighbour) or neighbour in previous:
                continue

            previous[neighbour] = (current, symbol)
            queue.append(neighbour)
            if neighbour == exit:
                queue.clear()
                break

    if exit not in previous:
        raise ValueError("exit is unreachable from entry")

    path: list[str] = []
    current = exit
    while current != entry:
        record = previous[current]
        if record is None:
            raise RuntimeError("path reconstruction reached the entry")
        parent, symbol = record
        path.append(symbol)
        current = parent

    return "".join(reversed(path))
