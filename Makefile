install:
	uv python install
	uv sync --locked
	uv pip install --link-mode=copy mlx-2.2-py3-none-any.whl

run:
	uv run python a_maze_ing.py config.txt

debug:
	uv run python -m pdb a_maze_ing.py config.txt

test:
	uv run python -m unittest discover -s test -v

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache

lint:
	uv run flake8 .
	uv run mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy --strict .

.PHONY: install run debug test clean lint lint-strict
