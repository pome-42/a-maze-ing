install:
	uv python install
	uv sync --locked

run:


debug:


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
