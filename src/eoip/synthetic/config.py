"""Central configuration contract for EOIP Phase 2 synthetic generation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    yaml = None


class GenerationProfile(StrEnum):
    """Supported named synthetic-data profiles."""

    UNIT = "unit"
    SMOKE = "smoke"
    DEFAULT = "default"
    EXTENDED = "extended"


class OutputFormat(StrEnum):
    """Supported synthetic output formats."""

    PARQUET = "parquet"
    CSV = "csv"


class CompressionCodec(StrEnum):
    """Supported artifact compression codecs."""

    ZSTD = "zstd"
    SNAPPY = "snappy"
    GZIP = "gzip"
    NONE = "none"


class OverwritePolicy(StrEnum):
    """Supported output-directory collision policies."""

    ERROR = "error"
    REPLACE = "replace"
    VERSION = "version"


@dataclass(frozen=True, slots=True)
class TimeRangeConfig:
    """UTC generation range with an exclusive end bound."""

    start: datetime
    end: datetime
    interval_minutes: int = 15

    def __post_init__(self) -> None:
        _validate_aware_datetime("start", self.start)
        _validate_aware_datetime("end", self.end)
        start = self.start.astimezone(UTC)
        end = self.end.astimezone(UTC)
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

        if end <= start:
            raise ValueError("end must be later than start.")
        if isinstance(self.interval_minutes, bool) or not isinstance(
            self.interval_minutes, int
        ):
            raise TypeError("interval_minutes must be an integer.")
        if self.interval_minutes not in {5, 10, 15, 30, 60}:
            raise ValueError("interval_minutes must be one of 5, 10, 15, 30, or 60.")
        for name, value in (("start", start), ("end", end)):
            if value.second != 0 or value.microsecond != 0:
                raise ValueError(f"{name} seconds and microseconds must be zero.")
            if value.minute % self.interval_minutes != 0:
                raise ValueError(f"{name} must align to interval_minutes.")
        seconds = (end - start).total_seconds()
        if seconds % (self.interval_minutes * 60) != 0:
            raise ValueError("The date range must contain complete intervals.")

    @property
    def interval_count(self) -> int:
        """Return the number of timestamps in the exclusive-end grid."""
        return int(
            (self.end - self.start).total_seconds() // (self.interval_minutes * 60)
        )

    @property
    def duration_days(self) -> float:
        """Return the configured duration in days."""
        return (self.end - self.start).total_seconds() / 86_400

    @property
    def final_timestamp(self) -> datetime:
        """Return the final included timestamp."""
        return self.end - timedelta(minutes=self.interval_minutes)


@dataclass(frozen=True, slots=True)
class PortfolioConfig:
    """Portfolio scale and capacity constraints."""

    plant_count: int
    aggregate_ac_capacity_min_mw: float = 750.0
    aggregate_ac_capacity_max_mw: float = 1_250.0
    plant_ac_capacity_min_mw: float = 20.0
    plant_ac_capacity_max_mw: float = 100.0
    inverter_count_min: int = 450
    inverter_count_max: int = 550

    def __post_init__(self) -> None:
        for name, value in (
            ("plant_count", self.plant_count),
            ("inverter_count_min", self.inverter_count_min),
            ("inverter_count_max", self.inverter_count_max),
        ):
            _validate_positive_integer(name, value)
        for name, value in (
            (
                "aggregate_ac_capacity_min_mw",
                self.aggregate_ac_capacity_min_mw,
            ),
            (
                "aggregate_ac_capacity_max_mw",
                self.aggregate_ac_capacity_max_mw,
            ),
            ("plant_ac_capacity_min_mw", self.plant_ac_capacity_min_mw),
            ("plant_ac_capacity_max_mw", self.plant_ac_capacity_max_mw),
        ):
            _validate_positive_number(name, value)

        if self.aggregate_ac_capacity_max_mw < self.aggregate_ac_capacity_min_mw:
            raise ValueError(
                "aggregate_ac_capacity_max_mw must be at least the minimum."
            )
        if self.plant_ac_capacity_max_mw < self.plant_ac_capacity_min_mw:
            raise ValueError("plant_ac_capacity_max_mw must be at least the minimum.")
        if self.inverter_count_max < self.inverter_count_min:
            raise ValueError("inverter_count_max must be at least the minimum.")


@dataclass(frozen=True, slots=True)
class WeatherConfig:
    """High-level weather-generation settings."""

    estimated_probability: float = 0.01
    missing_probability: float = 0.002
    cloud_autocorrelation: float = 0.92
    measurement_noise_pct: float = 1.5

    def __post_init__(self) -> None:
        _validate_probability("estimated_probability", self.estimated_probability)
        _validate_probability("missing_probability", self.missing_probability)
        _validate_probability("cloud_autocorrelation", self.cloud_autocorrelation)
        _validate_percentage("measurement_noise_pct", self.measurement_noise_pct, 20.0)
        if self.estimated_probability + self.missing_probability > 1.0:
            raise ValueError(
                "estimated_probability plus missing_probability must not " "exceed 1.0."
            )


@dataclass(frozen=True, slots=True)
class PhysicsConfig:
    """High-level physical generation and loss settings."""

    reference_irradiance_wm2: float = 1_000.0
    module_temperature_coefficient_per_c: float = -0.004
    transformer_loss_pct: float = 1.5
    collection_loss_pct: float = 1.0
    clipping_tolerance_pct: float = 0.5

    def __post_init__(self) -> None:
        _validate_positive_number(
            "reference_irradiance_wm2", self.reference_irradiance_wm2
        )
        coefficient = self.module_temperature_coefficient_per_c
        if isinstance(coefficient, bool) or not isinstance(coefficient, (int, float)):
            raise TypeError("module_temperature_coefficient_per_c must be numeric.")
        if not math.isfinite(coefficient) or not -0.02 <= coefficient <= 0:
            raise ValueError(
                "module_temperature_coefficient_per_c must be finite and "
                "between -0.02 and 0.0."
            )
        _validate_percentage("transformer_loss_pct", self.transformer_loss_pct, 20)
        _validate_percentage("collection_loss_pct", self.collection_loss_pct, 20)
        _validate_percentage("clipping_tolerance_pct", self.clipping_tolerance_pct, 10)
        if self.transformer_loss_pct + self.collection_loss_pct >= 100:
            raise ValueError("Combined electrical losses must be below 100 percent.")


@dataclass(frozen=True, slots=True)
class EventConfig:
    """High-level event and lifecycle conversion settings."""

    enabled: bool = True
    annual_event_rate_multiplier: float = 1.0
    incident_conversion_probability: float = 0.65
    work_order_conversion_probability: float = 0.55

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a boolean.")
        _validate_positive_number(
            "annual_event_rate_multiplier", self.annual_event_rate_multiplier
        )
        _validate_probability(
            "incident_conversion_probability",
            self.incident_conversion_probability,
        )
        _validate_probability(
            "work_order_conversion_probability",
            self.work_order_conversion_probability,
        )


@dataclass(frozen=True, slots=True)
class OutputConfig:
    """Artifact output and publication settings."""

    root: Path = Path("data/synthetic")
    format: OutputFormat = OutputFormat.PARQUET
    compression: CompressionCodec = CompressionCodec.ZSTD
    partition_timeseries: bool = True
    overwrite_policy: OverwritePolicy = OverwritePolicy.VERSION
    write_validation_report: bool = True
    write_manifest: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.root, Path):
            object.__setattr__(self, "root", Path(self.root))
        if not str(self.root).strip():
            raise ValueError("root cannot be empty.")
        if not isinstance(self.format, OutputFormat):
            raise TypeError("format must be an OutputFormat.")
        if not isinstance(self.compression, CompressionCodec):
            raise TypeError("compression must be a CompressionCodec.")
        if (
            self.format is OutputFormat.CSV
            and self.compression is CompressionCodec.SNAPPY
        ):
            raise ValueError("SNAPPY compression is not supported for CSV output.")
        if not isinstance(self.overwrite_policy, OverwritePolicy):
            raise TypeError("overwrite_policy must be an OverwritePolicy.")
        for name, value in (
            ("partition_timeseries", self.partition_timeseries),
            ("write_validation_report", self.write_validation_report),
            ("write_manifest", self.write_manifest),
        ):
            if not isinstance(value, bool):
                raise TypeError(f"{name} must be a boolean.")


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    """Validation tolerances and publication policy."""

    fail_on_warning: bool = False
    maximum_failure_samples: int = 20
    absolute_power_tolerance_kw: float = 0.1
    relative_power_tolerance_pct: float = 0.1
    energy_tolerance_kwh: float = 0.05
    allow_unexplained_time_gaps: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.fail_on_warning, bool):
            raise TypeError("fail_on_warning must be a boolean.")
        if not isinstance(self.allow_unexplained_time_gaps, bool):
            raise TypeError("allow_unexplained_time_gaps must be a boolean.")
        _validate_positive_integer(
            "maximum_failure_samples", self.maximum_failure_samples
        )
        _validate_non_negative_number(
            "absolute_power_tolerance_kw",
            self.absolute_power_tolerance_kw,
        )
        _validate_percentage(
            "relative_power_tolerance_pct",
            self.relative_power_tolerance_pct,
            10.0,
        )
        _validate_non_negative_number("energy_tolerance_kwh", self.energy_tolerance_kwh)


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    """Complete immutable configuration for one generation run."""

    profile_name: GenerationProfile
    seed: int
    time: TimeRangeConfig
    portfolio: PortfolioConfig
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    events: EventConfig = field(default_factory=EventConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    schema_version: str = "1.0.0"
    generator_version: str = "0.1.0"
    stream_version: str = "1.0.0"
    physics_version: str = "1.0.0"
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.profile_name, GenerationProfile):
            raise TypeError("profile_name must be a GenerationProfile.")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer.")
        if self.seed < 0:
            raise ValueError("seed must be greater than or equal to zero.")
        for name, value, expected in (
            ("time", self.time, TimeRangeConfig),
            ("portfolio", self.portfolio, PortfolioConfig),
            ("weather", self.weather, WeatherConfig),
            ("physics", self.physics, PhysicsConfig),
            ("events", self.events, EventConfig),
            ("output", self.output, OutputConfig),
            ("validation", self.validation, ValidationConfig),
        ):
            if not isinstance(value, expected):
                raise TypeError(f"{name} must be a {expected.__name__}.")
        for name, value in (
            ("schema_version", self.schema_version),
            ("generator_version", self.generator_version),
            ("stream_version", self.stream_version),
            ("physics_version", self.physics_version),
        ):
            _validate_non_empty_string(name, value)
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")
        normalized: dict[str, str] = {}
        for key, value in self.metadata.items():
            _validate_non_empty_string("metadata key", key)
            _validate_non_empty_string(f"metadata[{key!r}]", value)
            normalized[str(key)] = str(value)
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(sorted(normalized.items()))),
        )

    @property
    def expected_plant_scada_rows(self) -> int:
        """Return complete plant-SCADA row count."""
        return self.portfolio.plant_count * self.time.interval_count

    def to_dict(self) -> dict[str, Any]:
        """Return normalized JSON-compatible configuration values."""
        return _normalize(_dataclass_to_dict(self))

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint."""
        return config_fingerprint(self)


def named_profile(profile: GenerationProfile | str) -> GenerationConfig:
    """Return one supported named profile."""
    resolved = _coerce_profile(profile)
    if resolved is GenerationProfile.UNIT:
        return GenerationConfig(
            profile_name=resolved,
            seed=20_250_201,
            time=TimeRangeConfig(
                datetime(2025, 1, 1, tzinfo=UTC),
                datetime(2025, 1, 3, tzinfo=UTC),
            ),
            portfolio=PortfolioConfig(
                plant_count=1,
                aggregate_ac_capacity_min_mw=20,
                aggregate_ac_capacity_max_mw=100,
                inverter_count_min=1,
                inverter_count_max=50,
            ),
            output=OutputConfig(root=Path("data/synthetic/unit")),
        )
    if resolved is GenerationProfile.SMOKE:
        return GenerationConfig(
            profile_name=resolved,
            seed=20_250_201,
            time=TimeRangeConfig(
                datetime(2025, 1, 1, tzinfo=UTC),
                datetime(2025, 1, 15, tzinfo=UTC),
            ),
            portfolio=PortfolioConfig(
                plant_count=2,
                aggregate_ac_capacity_min_mw=40,
                aggregate_ac_capacity_max_mw=200,
                inverter_count_min=2,
                inverter_count_max=100,
            ),
            output=OutputConfig(root=Path("data/synthetic/smoke")),
        )
    if resolved is GenerationProfile.EXTENDED:
        return GenerationConfig(
            profile_name=resolved,
            seed=20_250_201,
            time=TimeRangeConfig(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2027, 1, 1, tzinfo=UTC),
            ),
            portfolio=PortfolioConfig(plant_count=20),
            output=OutputConfig(root=Path("data/synthetic/extended")),
        )
    return GenerationConfig(
        profile_name=GenerationProfile.DEFAULT,
        seed=20_250_201,
        time=TimeRangeConfig(
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
        portfolio=PortfolioConfig(plant_count=20),
        output=OutputConfig(root=Path("data/synthetic/default")),
    )


def load_generation_config(
    path_or_profile: str | Path | GenerationProfile = GenerationProfile.DEFAULT,
    *,
    overrides: Mapping[str, Any] | None = None,
) -> GenerationConfig:
    """Load a named profile or YAML file and apply explicit overrides."""
    if isinstance(path_or_profile, GenerationProfile):
        config = named_profile(path_or_profile)
    else:
        candidate = Path(path_or_profile)
        if candidate.suffix.lower() in {".yaml", ".yml"} or candidate.exists():
            config = _load_yaml(candidate)
        else:
            config = named_profile(str(path_or_profile))
    if overrides:
        config = _apply_overrides(config, overrides)
    validate_generation_config(config)
    return config


def validate_generation_config(config: GenerationConfig) -> None:
    """Validate cross-section configuration invariants."""
    if not isinstance(config, GenerationConfig):
        raise TypeError("config must be a GenerationConfig.")
    if config.profile_name is GenerationProfile.DEFAULT:
        if config.portfolio.plant_count != 20:
            raise ValueError("The default profile must contain exactly 20 plants.")
        if config.time.interval_minutes != 15:
            raise ValueError("The default profile must use 15-minute intervals.")
    if (
        config.profile_name is GenerationProfile.SMOKE
        and config.portfolio.plant_count != 2
    ):
        raise ValueError("The smoke profile must contain 2 plants.")
    if (
        config.profile_name is GenerationProfile.UNIT
        and config.portfolio.plant_count != 1
    ):
        raise ValueError("The unit profile must contain 1 plant.")


def config_fingerprint(config: GenerationConfig) -> str:
    """Return a deterministic SHA-256 hash of normalized configuration."""
    validate_generation_config(config)
    payload = json.dumps(
        config.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_yaml(path: Path) -> GenerationConfig:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML is required to load YAML profiles.")
    with path.open("r", encoding="utf-8") as stream:
        loaded = yaml.safe_load(stream) or {}
    if not isinstance(loaded, Mapping):
        raise TypeError("YAML configuration must contain a mapping.")
    base = named_profile(loaded.get("profile_name", "default"))
    return _apply_overrides(base, loaded)


def _apply_overrides(
    config: GenerationConfig,
    overrides: Mapping[str, Any],
) -> GenerationConfig:
    allowed = {
        "profile_name",
        "seed",
        "time",
        "portfolio",
        "weather",
        "physics",
        "events",
        "output",
        "validation",
        "schema_version",
        "generator_version",
        "stream_version",
        "physics_version",
        "metadata",
    }
    unknown = set(overrides) - allowed
    if unknown:
        raise ValueError("Unknown configuration keys: " + ", ".join(sorted(unknown)))
    result = config
    if "profile_name" in overrides:
        result = replace(
            result, profile_name=_coerce_profile(overrides["profile_name"])
        )
    scalar_names = (
        "seed",
        "schema_version",
        "generator_version",
        "stream_version",
        "physics_version",
        "metadata",
    )
    scalar_updates = {
        name: overrides[name] for name in scalar_names if name in overrides
    }
    if scalar_updates:
        result = replace(result, **scalar_updates)

    section_types = {
        "time": TimeRangeConfig,
        "portfolio": PortfolioConfig,
        "weather": WeatherConfig,
        "physics": PhysicsConfig,
        "events": EventConfig,
        "output": OutputConfig,
        "validation": ValidationConfig,
    }
    for name, section_type in section_types.items():
        if name not in overrides:
            continue
        values = overrides[name]
        if not isinstance(values, Mapping):
            raise TypeError(f"{name} overrides must be a mapping.")
        values = dict(values)
        if section_type is TimeRangeConfig:
            for key in ("start", "end"):
                if key in values:
                    values[key] = _parse_datetime(values[key], f"time.{key}")
        if section_type is OutputConfig:
            if "root" in values:
                values["root"] = Path(values["root"])
            if "format" in values:
                values["format"] = OutputFormat(values["format"])
            if "compression" in values:
                values["compression"] = CompressionCodec(values["compression"])
            if "overwrite_policy" in values:
                values["overwrite_policy"] = OverwritePolicy(values["overwrite_policy"])
        result = replace(
            result,
            **{name: replace(getattr(result, name), **values)},
        )
    return result


def _parse_datetime(value: Any, name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be a valid ISO-8601 datetime.") from exc
    else:
        raise TypeError(f"{name} must be a datetime or ISO-8601 string.")
    _validate_aware_datetime(name, parsed)
    return parsed.astimezone(UTC)


def _coerce_profile(value: GenerationProfile | str | Any) -> GenerationProfile:
    if isinstance(value, GenerationProfile):
        return value
    if not isinstance(value, str):
        raise TypeError("profile must be a profile enum or string.")
    try:
        return GenerationProfile(value.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in GenerationProfile)
        raise ValueError(
            f"Unknown generation profile '{value}'. Use: {allowed}."
        ) from exc


def _dataclass_to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {
            field.name: _dataclass_to_dict(getattr(value, field.name))
            for field in value.__dataclass_fields__.values()
        }
    if isinstance(value, MappingProxyType):
        return {str(key): _dataclass_to_dict(item) for key, item in value.items()}
    if isinstance(value, Mapping):
        return {str(key): _dataclass_to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dataclass_to_dict(item) for item in value]
    return value


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def _validate_aware_datetime(name: str, value: datetime) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")


def _validate_positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _validate_non_empty_string(name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if not value.strip():
        raise ValueError(f"{name} cannot be empty.")


def _validate_positive_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric.")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _validate_non_negative_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric.")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if value < 0:
        raise ValueError(f"{name} must be greater than or equal to zero.")


def _validate_probability(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric.")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


def _validate_percentage(name: str, value: float, maximum: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric.")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} must be between 0.0 and {maximum}.")


__all__ = [
    "CompressionCodec",
    "EventConfig",
    "GenerationConfig",
    "GenerationProfile",
    "OutputConfig",
    "OutputFormat",
    "OverwritePolicy",
    "PhysicsConfig",
    "PortfolioConfig",
    "TimeRangeConfig",
    "ValidationConfig",
    "WeatherConfig",
    "config_fingerprint",
    "load_generation_config",
    "named_profile",
    "validate_generation_config",
]
