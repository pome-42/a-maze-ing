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

    parts = value.split(",")
    if len(parts) != 2:
        raise ConfigError(f"{key} must contain exactly two coordinates")

    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError as error:
        raise ConfigError(f"{key} must contain two integers") from error


def _parse_integer(key: str, value: str) -> int:
    """Parse an integer configuration value."""

    try:
        return int(value)
    except ValueError as error:
        raise ConfigError(f"{key} must be an integer") from error


def load_config(path: str) -> Config:
    """Load, convert, and validate maze settings from a UTF-8 file."""

    values: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as config_file:
            for line_number, raw_line in enumerate(config_file, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                if line.count("=") != 1:
                    raise ConfigError(
                        f"line {line_number} must contain exactly one '='"
                    )

                key, value = (part.strip() for part in line.split("=", 1))
                if not key:
                    raise ConfigError(f"line {line_number} has an empty key")
                if not value:
                    raise ConfigError(f"line {line_number} has an empty value")
                if key not in SUPPORTED_KEYS:
                    raise ConfigError(f"unsupported configuration key: {key}")
                if key in values:
                    raise ConfigError(f"duplicate configuration key: {key}")
                values[key] = value
    except ConfigError:
        raise
    except OSError as error:
        message = f"cannot open configuration file: {path}"
        raise ConfigError(message) from error
    except UnicodeError as error:
        message = f"configuration file is not valid UTF-8: {path}"
        raise ConfigError(message) from error

    missing_keys = REQUIRED_KEYS - values.keys()
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ConfigError(f"missing required configuration keys: {missing}")

    width = _parse_integer("WIDTH", values["WIDTH"])
    height = _parse_integer("HEIGHT", values["HEIGHT"])

    if width <= 0:
        raise ConfigError("WIDTH must be greater than 0")
    if height <= 0:
        raise ConfigError("HEIGHT must be greater than 0")

    entry = _parse_coordinate("ENTRY", values["ENTRY"])
    exit_position = _parse_coordinate("EXIT", values["EXIT"])
    for key, position in (("ENTRY", entry), ("EXIT", exit_position)):
        x, y = position
        if not (0 <= x < width and 0 <= y < height):
            raise ConfigError(f"{key} must be within the maze bounds")
    if entry == exit_position:
        raise ConfigError("ENTRY and EXIT must be different")

    perfect_value = values["PERFECT"]
    if perfect_value not in {"True", "False"}:
        raise ConfigError("PERFECT must be exactly True or False")

    seed: int | None = None
    if "SEED" in values:
        seed = _parse_integer("SEED", values["SEED"])

    return Config(
        width=width,
        height=height,
        entry=entry,
        exit=exit_position,
        output_file=values["OUTPUT_FILE"],
        perfect=perfect_value == "True",
        seed=seed,
    )
