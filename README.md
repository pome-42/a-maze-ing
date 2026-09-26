*This project has been created as part of the 42 curriculum by yito, nshuhei.*

# Description

`A-Maze-ing` is a Python maze generator and visualizer. It reads a configuration
file, generates a validated maze, writes the maze using hexadecimal wall
encoding, calculates a shortest path from the entry to the exit, and displays
the result with MiniLibX.

The generator supports two modes:

- `PERFECT=True`: creates a perfect maze with exactly one route between cells.
- `PERFECT=False`: creates a connected Pac-Man-like board with multiple routes,
  accessible corners and centre, and few dead ends.

The generated maze also reserves closed cells forming a visible `42` pattern
when the configured dimensions allow it. For very small mazes, the pattern is
omitted and a warning is printed.

# Requirements

- Python 3.10 or later
- `uv`
- Linux MiniLibX, provided in this repository as `mlx-2.2-py3-none-any.whl`

# Instructions

## Installation with uv

```bash
make install
```

This installs the Python environment and the bundled MiniLibX wheel.

## Running the program

The mandatory usage is:

```bash
python3 a_maze_ing.py config.txt
```

When using the project virtual environment, run:

```bash
source .venv/bin/activate
python3 a_maze_ing.py config.txt
```

Alternatively, use the Makefile:

```bash
make run
```

The program writes the generated maze to the file specified by `OUTPUT_FILE`.
The graphical window supports the following controls:

| Key | Action |
| --- | --- |
| `1` | Generate and display another maze |
| `2` | Show or hide the shortest path |
| `3` | Cycle through wall colours |
| `4` or `Esc` | Quit |

## Development commands

```bash
make test
make lint
make debug
make clean
```

`make lint` runs flake8 and mypy with the flags required by the subject.

# Configuration file

The configuration file contains one `KEY=VALUE` pair per line. Empty lines and
lines beginning with `#` are ignored.

| Key | Description | Example |
| --- | --- | --- |
| `WIDTH` | Number of cells horizontally | `WIDTH=25` |
| `HEIGHT` | Number of cells vertically | `HEIGHT=20` |
| `ENTRY` | Entry coordinate as `x,y` | `ENTRY=0,0` |
| `EXIT` | Exit coordinate as `x,y` | `EXIT=24,19` |
| `OUTPUT_FILE` | Output file path | `OUTPUT_FILE=maze.txt` |
| `PERFECT` | Whether to generate a perfect maze | `PERFECT=False` |
| `SEED` | Optional integer seed for reproducibility | `SEED=42` |

The default `config.txt` in the repository is:

```text
WIDTH=25
HEIGHT=20
ENTRY=0,0
EXIT=24,19
OUTPUT_FILE=maze.txt
PERFECT=False
SEED=42
```

# Generation algorithm

The perfect maze is generated with a randomized depth-first search (recursive
backtracker) implemented iteratively with an explicit stack. The algorithm
carves a spanning tree through all playable cells, which guarantees
connectivity and no loops.

For non-perfect mazes, the spanning tree is extended by opening additional
candidate edges. Edges are selected using a heuristic that prefers reducing
dead ends while preserving the rule that no fully open 3x3 area may exist. The
algorithm stops only after at least two independent routes are available and
the number of dead ends is within the allowed limit.

The generator uses `random.Random(seed)`. Supplying the same seed and
parameters produces the same maze, while omitting the seed creates a fresh
64-bit seed.

# Output format

Each cell is written as one hexadecimal digit. The four low bits represent
closed walls:

| Bit | Direction |
| --- | --- |
| 0 | North |
| 1 | East |
| 2 | South |
| 3 | West |

Cells are written row by row. After an empty line, the output contains the
entry coordinate, the exit coordinate, and the shortest path using `N`, `E`,
`S`, and `W`, one item per line.

# Reusable generator package

The reusable API is provided by the `mazegen` package. It can be imported
without using the command-line interface or opening a graphical window.

```python
from mazegen import MazeGenerator

generator = MazeGenerator(
    25,
    20,
    seed=42,
    entry=(0, 0),
    exit=(24, 19),
    perfect=False,
)
result = generator.generate()

print(result.width, result.height)
print(result.grid)
print(result.solution)
```

`result.grid` exposes the immutable wall structure, `result.entry` and
`result.exit` expose the terminals, `result.solution` contains a shortest path,
and `result.pattern_cells` identifies the reserved `42` cells.

The package can be rebuilt from the repository with:

```bash
uv build --out-dir .
```

The generated `mazegen-*.whl` and `mazegen-*.tar.gz` files are the reusable
package artifacts.

# Project structure

- `a_maze_ing.py`: command-line entry point
- `config.py`, `maze_setup.py`: configuration parsing and setup
- `maze_generator.py`: maze generation implementation
- `maze.py`, `maze_types.py`: maze model and wall operations
- `maze_solver.py`: shortest-path calculation
- `maze_validator.py`: independent maze validation
- `maze_output.py`: hexadecimal output serialization
- `mlx_view.py`: MiniLibX visualizer
- `mazegen/__init__.py`: reusable public API
- `maze_analyzer.py`: output verification helper
- `test/`: unit tests

# Testing and validation

The project includes unit tests for configuration parsing, generation,
validation, solving, serialization, the reusable API, and the graphical view.
The generated output can also be checked with:

```bash
python3 maze_analyzer.py maze.txt
```

# Team and project management

## Team roles

- `yito`: maze generation, command-line flow, validation, output
  format, reusable package, and project integration.
- `nshuhei`: MiniLibX visual representation and related tests.

Both members reviewed the implementation and tested the complete workflow.

## Planning and evolution

The project was developed in stages: first the maze model and wall operations,
then configuration parsing and generation, followed by solving, validation,
serialization, the reusable package API, and the graphical display. Testing was
added alongside each component. During development, the initial perfect-maze
generator was extended with the non-perfect Pac-Man mode, independent
validation, reproducible seeds, and the visible `42` pattern.

The modular structure and independent validator worked well because generation
and output could be tested separately. The main improvement opportunity is to
make the display backend easier to run on systems where MiniLibX is not already
available.

# Resources

- Python standard library: data structures, randomness, file handling, and
  path-finding support.
- MiniLibX: graphical maze display.
- `uv`: Python version and dependency management.
- flake8, mypy, and unittest: code quality and automated testing.
- The included `maze_analyzer.py`: output-format and gameplay validation.

AI tools were used as development assistance for investigating errors,
reviewing requirements, suggesting test cases, and improving documentation.
All generated suggestions were reviewed, tested, and adapted by the team.
The team remains responsible for understanding and maintaining the submitted
code.

# License

The reusable generator is distributed under the license described in
`LICENSE.md`.
