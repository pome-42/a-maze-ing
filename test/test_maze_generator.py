"""Tests for the maze generator entry point."""

from dataclasses import FrozenInstanceError
from unittest import TestCase

from maze import Maze
from maze_generator import GeneratedMaze, MazeGenerator
from maze_types import ALL_WALLS, Coordinate, Wall
from maze_validator import MazeValidationInput, validate_maze


class MazeGeneratorTests(TestCase):
    """Verify validation of generator construction parameters."""

    def test_accepts_positive_dimensions_and_optional_seed(self) -> None:
        generator = MazeGenerator(10, 8, seed=42)

        self.assertEqual(generator.width, 10)
        self.assertEqual(generator.height, 8)
        self.assertEqual(generator.seed, 42)

    def test_accepts_seed_omission(self) -> None:
        generator = MazeGenerator(2, 2)

        self.assertIsInstance(generator.seed, int)

    def test_generated_maze_exposes_snapshots_and_metadata(self) -> None:
        maze = Maze(2, 2)
        pattern = {Coordinate(1, 1)}
        maze.reserve_pattern_cells(pattern)
        result = GeneratedMaze(
            maze,
            Coordinate(0, 0),
            Coordinate(1, 0),
            42,
            False,
        )

        self.assertEqual(result.grid, maze.grid)
        self.assertEqual(result.pattern_cells, frozenset(pattern))
        self.assertEqual(result.entry, Coordinate(0, 0))
        self.assertEqual(result.exit, Coordinate(1, 0))
        self.assertEqual(result.seed, 42)
        self.assertFalse(result.pattern_omitted)

    def test_generated_maze_metadata_is_immutable(self) -> None:
        result = GeneratedMaze(
            Maze(2, 2),
            Coordinate(0, 0),
            Coordinate(1, 0),
            42,
            False,
        )

        with self.assertRaises(FrozenInstanceError):
            result.seed = 42  # type: ignore[misc]

    def test_rejects_non_integer_dimensions(self) -> None:
        with self.assertRaises(TypeError):
            MazeGenerator("10", 8)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            MazeGenerator(10, 8.0)  # type: ignore[arg-type]

    def test_rejects_boolean_dimensions(self) -> None:
        with self.assertRaises(TypeError):
            MazeGenerator(True, 8)
        with self.assertRaises(TypeError):
            MazeGenerator(10, False)

    def test_rejects_non_positive_dimensions(self) -> None:
        with self.assertRaises(ValueError):
            MazeGenerator(0, 8)
        with self.assertRaises(ValueError):
            MazeGenerator(10, -1)

    def test_rejects_invalid_seed(self) -> None:
        with self.assertRaises(TypeError):
            MazeGenerator(10, 8, seed=True)
        with self.assertRaises(TypeError):
            MazeGenerator(10, 8, seed="42")  # type: ignore[arg-type]

    def test_generate_accepts_perfect_mode_flag(self) -> None:
        result = MazeGenerator(10, 8, seed=42).generate(perfect=True)

        self.assertEqual(result.seed, 42)

    def test_generate_rejects_invalid_perfect_mode_flag(self) -> None:
        with self.assertRaises(TypeError):
            MazeGenerator(10, 8).generate(
                perfect=1,  # type: ignore[arg-type]
            )

    def test_non_perfect_mode_is_explicitly_pending(self) -> None:
        with self.assertRaises(NotImplementedError):
            MazeGenerator(10, 8).generate(perfect=False)

    def test_converts_mask_ones_to_coordinates(self) -> None:
        generator = MazeGenerator(10, 8)

        cells = generator._mask_cells(Coordinate(0, 0))

        expected = {
            Coordinate(0, 0),
            Coordinate(4, 0),
            Coordinate(5, 0),
            Coordinate(6, 0),
            Coordinate(0, 1),
            Coordinate(6, 1),
            Coordinate(0, 2),
            Coordinate(1, 2),
            Coordinate(2, 2),
            Coordinate(4, 2),
            Coordinate(5, 2),
            Coordinate(6, 2),
            Coordinate(2, 3),
            Coordinate(4, 3),
            Coordinate(2, 4),
            Coordinate(4, 4),
            Coordinate(5, 4),
            Coordinate(6, 4),
        }

        self.assertEqual(cells, expected)

    def test_mask_coordinates_follow_origin_offset(self) -> None:
        generator = MazeGenerator(10, 8)

        cells = generator._mask_cells(Coordinate(2, 3))

        self.assertIn(Coordinate(2, 3), cells)
        self.assertIn(Coordinate(8, 7), cells)
        self.assertNotIn(Coordinate(0, 0), cells)

    def test_mask_fits_inside_the_maze(self) -> None:
        generator = MazeGenerator(10, 8)

        self.assertTrue(generator._mask_fits(Coordinate(0, 0)))
        self.assertTrue(generator._mask_fits(Coordinate(3, 3)))

    def test_mask_does_not_fit_when_it_exceeds_the_maze(self) -> None:
        generator = MazeGenerator(6, 8)

        self.assertFalse(generator._mask_fits(Coordinate(0, 0)))
        self.assertFalse(generator._mask_fits(Coordinate(4, 3)))

    def test_candidate_origins_prioritize_the_center(
        self,
    ) -> None:
        generator = MazeGenerator(10, 8)

        origins = generator._candidate_origins()

        self.assertEqual(origins[:4], [
            Coordinate(1, 1),
            Coordinate(2, 1),
            Coordinate(1, 2),
            Coordinate(2, 2),
        ])
        self.assertEqual(len(origins), 16)

    def test_candidate_origins_are_empty_when_mask_does_not_fit(self) -> None:
        self.assertEqual(
            MazeGenerator(6, 8)._candidate_origins(),
            [],
        )

    def test_exact_fit_has_one_candidate_origin(self) -> None:
        self.assertEqual(
            MazeGenerator(7, 5)._candidate_origins(),
            [Coordinate(0, 0)],
        )

    def test_terminal_overlap_is_removed_from_candidates(self) -> None:
        generator = MazeGenerator(10, 8)

        origins = generator._candidate_origins_without_terminals(
            Coordinate(0, 0),
            Coordinate(9, 7),
        )

        self.assertEqual(len(origins), 14)
        self.assertNotIn(Coordinate(0, 0), origins)
        self.assertNotIn(Coordinate(3, 3), origins)

    def test_non_overlapping_terminals_keep_all_candidates(self) -> None:
        generator = MazeGenerator(10, 8)

        origins = generator._candidate_origins_without_terminals(
            Coordinate(0, 6),
            Coordinate(1, 7),
        )

        self.assertEqual(len(origins), 16)

    def test_playable_cells_are_connected_without_pattern(self) -> None:
        generator = MazeGenerator(4, 3)

        self.assertTrue(
            generator._is_connected_without_pattern(
                {Coordinate(1, 1)},
                Coordinate(0, 0),
            )
        )

    def test_pattern_can_split_playable_cells(self) -> None:
        generator = MazeGenerator(5, 5)
        barrier = {Coordinate(2, y) for y in range(5)}

        self.assertFalse(
            generator._is_connected_without_pattern(
                barrier,
                Coordinate(0, 0),
            )
        )

    def test_starting_inside_pattern_is_not_playable(self) -> None:
        generator = MazeGenerator(4, 3)
        pattern = {Coordinate(1, 1)}

        self.assertFalse(
            generator._is_connected_without_pattern(
                pattern,
                Coordinate(1, 1),
            )
        )

    def test_selects_connected_pattern_avoiding_terminals(self) -> None:
        generator = MazeGenerator(10, 8)

        pattern_cells = generator._select_pattern_cells(
            Coordinate(0, 0),
            Coordinate(9, 7),
        )

        self.assertIsNotNone(pattern_cells)
        assert pattern_cells is not None
        self.assertNotIn(Coordinate(0, 0), pattern_cells)
        self.assertNotIn(Coordinate(9, 7), pattern_cells)
        self.assertTrue(
            generator._is_connected_without_pattern(
                pattern_cells,
                Coordinate(0, 0),
            )
        )

    def test_select_returns_none_when_pattern_does_not_fit(self) -> None:
        generator = MazeGenerator(6, 8)

        self.assertIsNone(
            generator._select_pattern_cells(
                Coordinate(0, 0),
                Coordinate(5, 7),
            )
        )

    def test_select_rejects_terminals_covering_only_candidate(self) -> None:
        generator = MazeGenerator(7, 5)

        with self.assertRaises(ValueError):
            generator._select_pattern_cells(
                Coordinate(0, 0),
                Coordinate(6, 0),
            )

    def test_reserves_selected_pattern_cells_in_maze(self) -> None:
        generator = MazeGenerator(10, 8)
        maze = Maze(10, 8)

        pattern_cells = generator._reserve_pattern(
            maze,
            Coordinate(0, 0),
            Coordinate(9, 7),
        )

        self.assertTrue(pattern_cells)
        self.assertEqual(maze.pattern_cells, pattern_cells)
        self.assertTrue(
            all(maze.get_walls(cell) == ALL_WALLS for cell in pattern_cells)
        )

    def test_reserve_returns_empty_for_small_maze(self) -> None:
        generator = MazeGenerator(6, 8)
        maze = Maze(6, 8)

        pattern_cells = generator._reserve_pattern(
            maze,
            Coordinate(0, 0),
            Coordinate(5, 7),
        )

        self.assertEqual(pattern_cells, set())
        self.assertEqual(maze.pattern_cells, frozenset())

    def test_reserve_propagates_terminal_collision(self) -> None:
        generator = MazeGenerator(7, 5)
        maze = Maze(7, 5)

        with self.assertRaises(ValueError):
            generator._reserve_pattern(
                maze,
                Coordinate(0, 0),
                Coordinate(6, 0),
            )

    def test_in_bounds_checks_coordinate_edges(self) -> None:
        generator = MazeGenerator(4, 3)

        self.assertTrue(generator._in_bounds(Coordinate(0, 0)))
        self.assertTrue(generator._in_bounds(Coordinate(3, 2)))
        self.assertFalse(generator._in_bounds(Coordinate(-1, 0)))
        self.assertFalse(generator._in_bounds(Coordinate(4, 2)))
        self.assertFalse(generator._in_bounds(Coordinate(3, 3)))

    def test_validate_terminals_accepts_distinct_in_bounds_coordinates(
        self,
    ) -> None:
        generator = MazeGenerator(4, 3)

        generator._validate_terminals(
            Coordinate(0, 0),
            Coordinate(3, 2),
        )

    def test_validate_terminals_rejects_invalid_coordinates(self) -> None:
        generator = MazeGenerator(4, 3)

        with self.assertRaises(TypeError):
            generator._validate_terminals(
                (0, 0),  # type: ignore[arg-type]
                Coordinate(3, 2),
            )
        with self.assertRaises(ValueError):
            generator._validate_terminals(
                Coordinate(-1, 0),
                Coordinate(3, 2),
            )
        with self.assertRaises(ValueError):
            generator._validate_terminals(
                Coordinate(1, 1),
                Coordinate(1, 1),
            )

    def test_playable_cells_exclude_pattern_cells(self) -> None:
        generator = MazeGenerator(3, 2)
        pattern_cells = {Coordinate(1, 0), Coordinate(2, 1)}

        playable = generator._playable_cells(pattern_cells)

        self.assertEqual(
            playable,
            {
                Coordinate(0, 0),
                Coordinate(2, 0),
                Coordinate(0, 1),
                Coordinate(1, 1),
            },
        )

    def test_playable_cells_do_not_mutate_pattern_input(self) -> None:
        generator = MazeGenerator(3, 2)
        pattern_cells = {Coordinate(1, 0)}

        generator._playable_cells(pattern_cells)

        self.assertEqual(pattern_cells, {Coordinate(1, 0)})

    def test_neighbours_at_corner_are_in_bounds_in_fixed_order(self) -> None:
        generator = MazeGenerator(2, 2)

        self.assertEqual(
            generator._neighbours(Coordinate(0, 0)),
            [
                (Coordinate(1, 0), Wall.EAST),
                (Coordinate(0, 1), Wall.SOUTH),
            ],
        )

    def test_neighbours_at_center_include_all_four_directions(self) -> None:
        generator = MazeGenerator(3, 3)

        self.assertEqual(
            generator._neighbours(Coordinate(1, 1)),
            [
                (Coordinate(1, 0), Wall.NORTH),
                (Coordinate(2, 1), Wall.EAST),
                (Coordinate(1, 2), Wall.SOUTH),
                (Coordinate(0, 1), Wall.WEST),
            ],
        )

    def test_carve_tree_connects_every_playable_cell_without_loops(
        self,
    ) -> None:
        generator = MazeGenerator(3, 2, seed=42)
        maze = Maze(3, 2)
        playable = generator._playable_cells(set())

        generator._carve_tree(maze, playable, Coordinate(0, 0))

        edge_count = 0
        for y in range(2):
            for x in range(3):
                if x < 2 and not maze.get_walls(
                    Coordinate(x, y)
                ) & Wall.EAST:
                    edge_count += 1
                if y < 1 and not maze.get_walls(
                    Coordinate(x, y)
                ) & Wall.SOUTH:
                    edge_count += 1
        self.assertEqual(edge_count, len(playable) - 1)

    def test_carve_tree_keeps_pattern_cell_closed(self) -> None:
        generator = MazeGenerator(3, 2, seed=42)
        maze = Maze(3, 2)
        pattern = {Coordinate(1, 1)}
        maze.reserve_pattern_cells(pattern)

        generator._carve_tree(
            maze,
            generator._playable_cells(pattern),
            Coordinate(0, 0),
        )

        self.assertEqual(maze.get_walls(Coordinate(1, 1)), ALL_WALLS)

    def test_carve_tree_rejects_start_inside_pattern(self) -> None:
        generator = MazeGenerator(3, 2)
        maze = Maze(3, 2)
        pattern = {Coordinate(1, 1)}

        with self.assertRaises(ValueError):
            generator._carve_tree(
                maze,
                generator._playable_cells(pattern),
                Coordinate(1, 1),
            )

    def test_generate_returns_a_valid_perfect_maze(self) -> None:
        result = MazeGenerator(10, 8, seed=42).generate(
            Coordinate(0, 0),
            Coordinate(9, 7),
        )

        report = validate_maze(
            MazeValidationInput(
                grid=result.grid,
                width=10,
                height=8,
                entry=result.entry,
                exit=result.exit,
                pattern_cells=result.pattern_cells,
                perfect=True,
            )
        )

        self.assertTrue(report.is_valid, report.errors)
        self.assertEqual(report.loop_count, 0)

    def test_generate_is_reproducible_with_same_seed(self) -> None:
        first = MazeGenerator(10, 8, seed=42).generate()
        second = MazeGenerator(10, 8, seed=42).generate()

        self.assertEqual(first.grid, second.grid)
        self.assertEqual(first.pattern_cells, second.pattern_cells)

    def test_omitted_seed_can_be_reused_for_reproduction(self) -> None:
        first = MazeGenerator(10, 8).generate()
        replay = MazeGenerator(10, 8, seed=first.seed).generate()

        self.assertIsInstance(first.seed, int)
        self.assertEqual(first.grid, replay.grid)
        self.assertEqual(first.pattern_cells, replay.pattern_cells)

    def test_different_seeds_can_change_generated_grid(self) -> None:
        first = MazeGenerator(10, 8, seed=1).generate()
        second = MazeGenerator(10, 8, seed=2).generate()

        self.assertNotEqual(first.grid, second.grid)

    def test_generate_uses_bottom_right_exit_by_default(self) -> None:
        result = MazeGenerator(4, 3, seed=42).generate()

        self.assertEqual(result.entry, Coordinate(0, 0))
        self.assertEqual(result.exit, Coordinate(3, 2))

    def test_generate_omits_pattern_for_small_maze(self) -> None:
        result = MazeGenerator(6, 4, seed=42).generate()

        self.assertEqual(result.pattern_cells, frozenset())
        self.assertTrue(result.pattern_omitted)

    def test_generate_rejects_geometric_fit_without_valid_placement(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            MazeGenerator(7, 5, seed=42).generate()

    def test_generate_validates_multiple_sizes_and_seeds(self) -> None:
        cases = (
            (2, 2),
            (6, 4),
            (8, 7),
            (9, 6),
            (10, 8),
            (11, 9),
        )
        seeds = (None, 0, 1, 42)

        for width, height in cases:
            for seed in seeds:
                with self.subTest(
                    width=width,
                    height=height,
                    seed=seed,
                ):
                    result = MazeGenerator(
                        width,
                        height,
                        seed=seed,
                    ).generate()
                    report = validate_maze(
                        MazeValidationInput(
                            grid=result.grid,
                            width=width,
                            height=height,
                            entry=result.entry,
                            exit=result.exit,
                            pattern_cells=result.pattern_cells,
                            perfect=True,
                        )
                    )

                    self.assertTrue(report.is_valid, report.errors)
                    self.assertEqual(report.loop_count, 0)
