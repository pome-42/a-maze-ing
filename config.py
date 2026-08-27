"""Configuration data model for the maze application."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Store validated maze-generation settings."""

    width: int
    height: int
    entry: tuple[int, int]
    exit: tuple[int, int]
    output_file: str
    perfect: bool
    seed: int | None = None
