install:
    uv python install
    uv sync --locked

run:


debug:


clean:
    rm -rf __pycache__ .mypy_cache .pytest_cache


lint:
   uv run flake8 .
   uv run mypy .

lint-strict:


.PHONY: install run debug clean lint lint-strict
