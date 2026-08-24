"""Unit tests for the EOIP Phase 2 synthetic configuration contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eoip.synthetic.config import (
    CompressionCodec,
    GenerationConfig,
    GenerationProfile,
    OutputConfig,
    OutputFormat,
    OverwritePolicy,
    PortfolioConfig,
    TimeRangeConfig,
    config_fingerprint,
    load_generation_config,
    named_profile,
    validate_generation_config,
)


def test_default_profile_contract() -> None:
    """Verify the approved default Phase 2 dataset contract."""
    config = named_profile(GenerationProfile.DEFAULT)

    assert config.profile_name is GenerationProfile.DEFAULT
    assert config.seed == 20_250_201
    assert config.portfolio.plant_count == 20
    assert config.time.start == datetime(2025, 1, 1, tzinfo=UTC)
    assert config.time.end == datetime(2026, 1, 1, tzinfo=UTC)
    assert config.time.interval_minutes == 15
    assert config.time.interval_count == 35_040
    assert config.expected_plant_scada_rows == 700_800


@pytest.mark.parametrize(
    ("profile", "plant_count"),
    [
        (GenerationProfile.UNIT, 1),
        (GenerationProfile.SMOKE, 2),
        (GenerationProfile.DEFAULT, 20),
        (GenerationProfile.EXTENDED, 20),
    ],
)
def test_named_profiles(profile: GenerationProfile, plant_count: int) -> None:
    """Verify every supported profile can be constructed."""
    config = named_profile(profile)

    assert config.profile_name is profile
    assert config.portfolio.plant_count == plant_count
    validate_generation_config(config)


def test_profile_name_string_is_supported() -> None:
    """Verify profile names may be supplied as strings."""
    assert named_profile("smoke").profile_name is GenerationProfile.SMOKE


def test_unknown_profile_is_rejected() -> None:
    """Verify unsupported profile names fail clearly."""
    with pytest.raises(ValueError, match="Unknown generation profile"):
        named_profile("production")


def test_time_range_uses_exclusive_end() -> None:
    """Verify the time grid treats end as exclusive."""
    config = TimeRangeConfig(
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2025, 1, 2, tzinfo=UTC),
        interval_minutes=15,
    )

    assert config.interval_count == 96
    assert config.final_timestamp == datetime(2025, 1, 1, 23, 45, tzinfo=UTC)


def test_time_range_normalizes_to_utc() -> None:
    """Verify aware timestamps are normalized to UTC."""
    config = TimeRangeConfig(
        start=datetime.fromisoformat("2025-01-01T05:00:00+05:00"),
        end=datetime.fromisoformat("2025-01-02T05:00:00+05:00"),
    )

    assert config.start == datetime(2025, 1, 1, tzinfo=UTC)
    assert config.end == datetime(2025, 1, 2, tzinfo=UTC)


def test_naive_time_range_is_rejected() -> None:
    """Verify generation timestamps must be timezone-aware."""
    with pytest.raises(ValueError, match="timezone-aware"):
        TimeRangeConfig(
            start=datetime(2025, 1, 1),
            end=datetime(2025, 1, 2, tzinfo=UTC),
        )


def test_non_aligned_time_range_is_rejected() -> None:
    """Verify timestamps align with the configured interval."""
    with pytest.raises(ValueError, match="align"):
        TimeRangeConfig(
            start=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
            end=datetime(2025, 1, 2, tzinfo=UTC),
            interval_minutes=15,
        )


def test_invalid_interval_is_rejected() -> None:
    """Verify only supported generation intervals are accepted."""
    with pytest.raises(ValueError, match="interval_minutes"):
        TimeRangeConfig(
            start=datetime(2025, 1, 1, tzinfo=UTC),
            end=datetime(2025, 1, 2, tzinfo=UTC),
            interval_minutes=7,
        )


def test_invalid_portfolio_bounds_are_rejected() -> None:
    """Verify portfolio capacity bounds remain internally consistent."""
    with pytest.raises(ValueError, match="plant_ac_capacity_max_mw"):
        PortfolioConfig(
            plant_count=20,
            plant_ac_capacity_min_mw=100.0,
            plant_ac_capacity_max_mw=20.0,
        )


def test_output_config_normalizes_root_to_path() -> None:
    """Verify string output roots become pathlib paths."""
    config = OutputConfig(root="data/example")

    assert config.root == Path("data/example")


def test_invalid_csv_snappy_combination_is_rejected() -> None:
    """Verify unsupported CSV/Snappy output is rejected."""
    with pytest.raises(ValueError, match="SNAPPY"):
        OutputConfig(
            format=OutputFormat.CSV,
            compression=CompressionCodec.SNAPPY,
        )


def test_configuration_is_immutable() -> None:
    """Verify top-level generation configuration is frozen."""
    config = named_profile("default")

    with pytest.raises(FrozenInstanceError):
        config.seed = 1  # type: ignore[misc]


def test_to_dict_is_json_compatible() -> None:
    """Verify normalized configuration contains portable values."""
    data = named_profile("default").to_dict()

    assert data["profile_name"] == "default"
    assert data["time"]["start"] == "2025-01-01T00:00:00Z"
    assert data["output"]["root"] == "data/synthetic/default"
    assert data["output"]["format"] == "parquet"


def test_fingerprint_is_deterministic() -> None:
    """Verify identical configuration produces the same fingerprint."""
    first = named_profile("default")
    second = named_profile("default")

    assert first.fingerprint() == second.fingerprint()
    assert first.fingerprint() == config_fingerprint(first)
    assert len(first.fingerprint()) == 64


def test_fingerprint_changes_when_seed_changes() -> None:
    """Verify material configuration changes alter the fingerprint."""
    default = named_profile("smoke")
    changed = load_generation_config(
        "smoke",
        overrides={"seed": default.seed + 1},
    )

    assert default.fingerprint() != changed.fingerprint()


def test_explicit_nested_overrides_are_applied() -> None:
    """Verify explicit nested configuration overrides."""
    config = load_generation_config(
        "smoke",
        overrides={
            "seed": 123,
            "output": {
                "root": "data/custom",
                "overwrite_policy": "replace",
            },
            "validation": {
                "maximum_failure_samples": 5,
            },
        },
    )

    assert config.seed == 123
    assert config.output.root == Path("data/custom")
    assert config.output.overwrite_policy is OverwritePolicy.REPLACE
    assert config.validation.maximum_failure_samples == 5


def test_unknown_override_key_is_rejected() -> None:
    """Verify misspelled or unsupported top-level keys fail."""
    with pytest.raises(ValueError, match="Unknown configuration keys"):
        load_generation_config(
            "smoke",
            overrides={"unknown_setting": True},
        )


def test_metadata_is_sorted_and_immutable() -> None:
    """Verify run metadata cannot be mutated after construction."""
    config = load_generation_config(
        "smoke",
        overrides={"metadata": {"z": "last", "a": "first"}},
    )

    assert list(config.metadata) == ["a", "z"]

    with pytest.raises(TypeError):
        config.metadata["new"] = "value"  # type: ignore[index]


def test_yaml_profile_and_overrides(tmp_path: Path) -> None:
    """Verify YAML files layer explicit values over a named profile."""
    pytest.importorskip("yaml")

    path = tmp_path / "generation.yaml"
    path.write_text(
        "\n".join(
            [
                "profile_name: smoke",
                "seed: 777",
                "time:",
                "  start: '2025-02-01T00:00:00Z'",
                "  end: '2025-02-03T00:00:00Z'",
                "output:",
                "  root: data/yaml-test",
                "  compression: gzip",
            ]
        ),
        encoding="utf-8",
    )

    config = load_generation_config(path)

    assert config.profile_name is GenerationProfile.SMOKE
    assert config.seed == 777
    assert config.time.start == datetime(2025, 2, 1, tzinfo=UTC)
    assert config.time.end == datetime(2025, 2, 3, tzinfo=UTC)
    assert config.output.root == Path("data/yaml-test")
    assert config.output.compression is CompressionCodec.GZIP


def test_missing_yaml_file_is_rejected(tmp_path: Path) -> None:
    """Verify explicit YAML paths must exist."""
    with pytest.raises(FileNotFoundError):
        load_generation_config(tmp_path / "missing.yaml")


def test_validate_requires_generation_config() -> None:
    """Verify cross-section validation rejects unrelated objects."""
    with pytest.raises(TypeError, match="GenerationConfig"):
        validate_generation_config(object())  # type: ignore[arg-type]


def test_default_profile_invariant_rejects_changed_plant_count() -> None:
    """Verify default-profile scale cannot silently drift."""
    base = named_profile("default")

    altered = GenerationConfig(
        profile_name=GenerationProfile.DEFAULT,
        seed=base.seed,
        time=base.time,
        portfolio=PortfolioConfig(
            plant_count=19,
            aggregate_ac_capacity_min_mw=750.0,
            aggregate_ac_capacity_max_mw=1_250.0,
            plant_ac_capacity_min_mw=20.0,
            plant_ac_capacity_max_mw=100.0,
            inverter_count_min=450,
            inverter_count_max=550,
        ),
        weather=base.weather,
        physics=base.physics,
        events=base.events,
        output=base.output,
        validation=base.validation,
    )

    with pytest.raises(ValueError, match="exactly 20 plants"):
        validate_generation_config(altered)
