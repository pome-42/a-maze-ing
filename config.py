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


def _parse_coordinate(key: str, value: str) -> tuple[int, int]:
    """Parse a configuration coordinate value."""

    parts: list[str] = value.split(",")
    if len(parts) != 2:
        raise ConfigError(f"{key} must contain exactly two coordinates")

    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError as error:
        raise ConfigError(f"{key} must contain two integers") from error
