"""Configuration data model for the maze application."""

from dataclasses import dataclass


REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "WIDTH",
        "HEIGHT",
        "ENTRY",
        "EXIT",
        "OUTPUT_FILE",
        "PERFECT",
    }
)
SUPPORTED_KEYS: frozenset[str] = REQUIRED_KEYS | {"SEED"}


class ConfigError(ValueError):
    """Raised when a maze configuration is invalid."""


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
