"""
Unit tests for the EOIP Phase 2 tariff DataFrame generator.

These tests verify deterministic tariff generation, effective-date coverage,
flat and time-of-use structures, stable identifiers, configuration validation,
currency handling, output schema, and generated DataFrame integrity.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, time
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest

from eoip.synthetic.generators.tariffs import (
    TariffGeneratorConfig,
    TariffWindow,
    generate_tariffs,
)


def _plants_frame() -> pd.DataFrame:
    """Return compact plant master data for tariff tests."""
    return pd.DataFrame(
        [
            {"plant_id": "PLT-001", "currency": "PKR"},
            {"plant_id": "PLT-002", "currency": "USD"},
            {"plant_id": "PLT-003", "currency": "EUR"},
        ]
    )


def _time_range() -> SimpleNamespace:
    """Return the standard inclusive/exclusive tariff period."""
    return SimpleNamespace(
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _config(**overrides: Any) -> TariffGeneratorConfig:
    """Return deterministic tariff configuration with optional overrides."""
    data: dict[str, Any] = {
        "random_seed": 20250201,
        "currency_default": "PKR",
        "flat_tariff_probability": 1.0,
        "minimum_rate_per_mwh": 20_000.0,
        "maximum_rate_per_mwh": 20_000.0,
        "minimum_escalation_ratio": 0.05,
        "maximum_escalation_ratio": 0.05,
        "contract_name_prefix": "EOIP Contract",
        "schema_version": "1.0.0",
    }
    data.update(overrides)
    return TariffGeneratorConfig(**data)


def test_generate_flat_tariffs_returns_expected_dataframe() -> None:
    """Flat generation should create one row per plant."""
    frame = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(flat_tariff_probability=1.0),
        generation_run_id="RUN-TEST",
    )

    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 3
    assert list(frame["plant_id"]) == [
        "PLT-001",
        "PLT-002",
        "PLT-003",
    ]
    assert set(frame["tariff_type"]) == {"flat"}
    assert set(frame["window_code"]) == {"FLAT"}


def test_generate_tou_tariffs_returns_four_windows_per_plant() -> None:
    """TOU generation should create four configured windows per plant."""
    frame = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(flat_tariff_probability=0.0),
    )

    assert len(frame) == 12
    assert set(frame["tariff_type"]) == {"time_of_use"}
    assert set(frame["window_code"]) == {
        "OFF_PEAK",
        "SHOULDER_AM",
        "PEAK",
        "SHOULDER_PM",
    }


def test_tariff_ids_are_stable_and_sequential() -> None:
    """Plant ordering should map to stable TRF identifiers."""
    frame = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(flat_tariff_probability=1.0),
    )

    assert list(frame["tariff_id"]) == [
        "TRF-0001",
        "TRF-0002",
        "TRF-0003",
    ]


def test_output_column_order_is_stable() -> None:
    """Generated DataFrame columns should match the public contract."""
    frame = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(),
    )

    assert tuple(frame.columns) == (
        "tariff_id",
        "plant_id",
        "tariff_type",
        "contract_name",
        "currency",
        "effective_start_date",
        "effective_end_date",
        "window_code",
        "local_start_time",
        "local_end_time",
        "day_category",
        "energy_rate_per_mwh",
        "annual_escalation_ratio",
        "generation_run_id",
        "schema_version",
    )


def test_effective_date_coverage_matches_time_range() -> None:
    """Tariff coverage should span the full inclusive calendar year."""
    frame = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(),
    )

    assert set(frame["effective_start_date"]) == {
        datetime(2025, 1, 1, tzinfo=UTC).date()
    }
    assert set(frame["effective_end_date"]) == {
        datetime(2025, 12, 31, tzinfo=UTC).date()
    }


def test_non_midnight_end_extends_to_containing_date() -> None:
    """A non-midnight exclusive end should cover its containing date."""
    time_range = {
        "start": datetime(2025, 1, 1, tzinfo=UTC),
        "end": datetime(2025, 1, 31, 12, 0, tzinfo=UTC),
    }

    frame = generate_tariffs(
        _plants_frame().iloc[:1],
        time_range,
        _config(),
    )

    assert (
        frame.loc[0, "effective_end_date"]
        == datetime(
            2025,
            1,
            31,
            tzinfo=UTC,
        ).date()
    )


def test_generation_is_deterministic() -> None:
    """Identical inputs should generate identical logical tariff rows."""
    first = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(flat_tariff_probability=0.5),
    )
    second = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(flat_tariff_probability=0.5),
    )

    pd.testing.assert_frame_equal(first, second)


def test_different_seed_changes_stochastic_values() -> None:
    """Different seeds should alter tariff choices or numeric values."""
    first = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(
            random_seed=1,
            flat_tariff_probability=0.5,
            minimum_rate_per_mwh=18_000.0,
            maximum_rate_per_mwh=32_000.0,
        ),
    )
    second = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(
            random_seed=2,
            flat_tariff_probability=0.5,
            minimum_rate_per_mwh=18_000.0,
            maximum_rate_per_mwh=32_000.0,
        ),
    )

    assert not first.equals(second)


def test_currency_comes_from_plant_master_data() -> None:
    """Plant-specific currencies should be preserved."""
    frame = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(),
    )

    assert dict(zip(frame["plant_id"], frame["currency"], strict=True)) == {
        "PLT-001": "PKR",
        "PLT-002": "USD",
        "PLT-003": "EUR",
    }


def test_missing_currency_uses_default() -> None:
    """Plants without currency should use the configured default."""
    plants = pd.DataFrame(
        [
            {"plant_id": "PLT-001", "currency": None},
            {"plant_id": "PLT-002", "currency": ""},
        ]
    )

    frame = generate_tariffs(
        plants,
        _time_range(),
        _config(currency_default="usd"),
    )

    assert set(frame["currency"]) == {"USD"}


def test_flat_tariffs_do_not_have_time_windows() -> None:
    """Flat tariff rows should leave local time columns null."""
    frame = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(flat_tariff_probability=1.0),
    )

    assert frame["local_start_time"].isna().all()
    assert frame["local_end_time"].isna().all()


def test_tou_tariffs_have_local_time_windows() -> None:
    """TOU tariff rows should serialize local start and end times."""
    frame = generate_tariffs(
        _plants_frame().iloc[:1],
        _time_range(),
        _config(flat_tariff_probability=0.0),
    )

    assert frame["local_start_time"].notna().all()
    assert frame["local_end_time"].notna().all()
    assert set(frame["local_start_time"]) == {
        "00:00:00",
        "07:00:00",
        "17:00:00",
        "22:00:00",
    }


def test_tou_rates_apply_expected_multipliers() -> None:
    """TOU windows should apply configured rate multipliers."""
    frame = generate_tariffs(
        _plants_frame().iloc[:1],
        _time_range(),
        _config(
            flat_tariff_probability=0.0,
            minimum_rate_per_mwh=20_000.0,
            maximum_rate_per_mwh=20_000.0,
        ),
    )

    rates = dict(
        zip(
            frame["window_code"],
            frame["energy_rate_per_mwh"],
            strict=True,
        )
    )

    assert rates == {
        "OFF_PEAK": 16_400.0,
        "PEAK": 25_000.0,
        "SHOULDER_AM": 20_000.0,
        "SHOULDER_PM": 18_400.0,
    }


def test_primary_key_is_unique() -> None:
    """Generated tariff and window keys should be unique."""
    frame = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(flat_tariff_probability=0.0),
    )

    assert not frame[["tariff_id", "window_code"]].duplicated().any()


def test_audit_columns_use_supplied_values() -> None:
    """Run ID and schema version should be included in every row."""
    frame = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(schema_version="2.0.0"),
        generation_run_id="RUN-ABC",
    )

    assert set(frame["generation_run_id"]) == {"RUN-ABC"}
    assert set(frame["schema_version"]) == {"2.0.0"}


def test_iterable_domain_objects_are_supported() -> None:
    """The generator should accept iterable plant-like objects."""
    plants = [
        SimpleNamespace(plant_id="PLT-002", currency="USD"),
        SimpleNamespace(plant_id="PLT-001", currency="PKR"),
    ]

    frame = generate_tariffs(
        plants,
        _time_range(),
        _config(),
    )

    assert list(frame["plant_id"]) == ["PLT-001", "PLT-002"]


def test_custom_tou_windows_are_supported() -> None:
    """Callers should be able to provide validated TOU windows."""
    windows = (
        TariffWindow(
            window_code="DAY",
            day_category="all_days",
            local_start_time=time(6, 0),
            local_end_time=time(18, 0),
            rate_multiplier=1.1,
        ),
        TariffWindow(
            window_code="NIGHT",
            day_category="all_days",
            local_start_time=time(18, 0),
            local_end_time=time(6, 0),
            rate_multiplier=0.8,
        ),
    )

    frame = generate_tariffs(
        _plants_frame().iloc[:1],
        _time_range(),
        _config(flat_tariff_probability=0.0),
        tou_windows=windows,
    )

    assert set(frame["window_code"]) == {"DAY", "NIGHT"}


class _FakeRandomContext:
    """Simple deterministic RandomContext test double."""

    def generator(
        self,
        name: str,
        entity_id: str | None = None,
    ) -> np.random.Generator:
        assert name == "tariffs"
        assert entity_id is not None
        entropy = sum(ord(character) for character in entity_id)
        return np.random.default_rng(entropy)


def test_random_context_is_used_when_supplied() -> None:
    """An explicit random context should drive generation."""
    context = _FakeRandomContext()

    first = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(random_seed=1),
        random_context=context,
    )
    second = generate_tariffs(
        _plants_frame(),
        _time_range(),
        _config(random_seed=999),
        random_context=context,
    )

    pd.testing.assert_frame_equal(first, second)


def test_config_normalizes_text_values() -> None:
    """Configuration text fields should be normalized."""
    config = TariffGeneratorConfig(
        currency_default=" pkr ",
        contract_name_prefix=" EOIP Contract ",
        schema_version=" 1.0.0 ",
    )

    assert config.currency_default == "PKR"
    assert config.contract_name_prefix == "EOIP Contract"
    assert config.schema_version == "1.0.0"


def test_config_is_immutable() -> None:
    """TariffGeneratorConfig should be frozen."""
    config = TariffGeneratorConfig()

    with pytest.raises(FrozenInstanceError):
        config.random_seed = 1  # type: ignore[misc]


@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_config_rejects_invalid_seed_type(value: object) -> None:
    """random_seed must be an integer excluding booleans."""
    with pytest.raises(TypeError, match="random_seed must be an integer"):
        TariffGeneratorConfig(random_seed=value)  # type: ignore[arg-type]


def test_config_rejects_negative_seed() -> None:
    """random_seed must be non-negative."""
    with pytest.raises(ValueError, match="random_seed must be non-negative"):
        TariffGeneratorConfig(random_seed=-1)


@pytest.mark.parametrize("value", ["", "US", "USDD", "1PK"])
def test_config_rejects_invalid_default_currency(value: str) -> None:
    """Default currency must contain exactly three letters."""
    with pytest.raises(ValueError, match="three-letter"):
        TariffGeneratorConfig(currency_default=value)


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_config_rejects_probability_outside_bounds(value: float) -> None:
    """Flat-tariff probability must remain between zero and one."""
    with pytest.raises(ValueError, match="between 0 and 1"):
        TariffGeneratorConfig(flat_tariff_probability=value)


@pytest.mark.parametrize("value", [True, "0.5", None])
def test_config_rejects_non_numeric_probability(value: object) -> None:
    """Flat-tariff probability must be numeric."""
    with pytest.raises(TypeError, match="must be numeric"):
        TariffGeneratorConfig(flat_tariff_probability=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_rate_per_mwh",
        "maximum_rate_per_mwh",
        "minimum_escalation_ratio",
        "maximum_escalation_ratio",
    ],
)
@pytest.mark.parametrize("value", [True, "1", None])
def test_config_rejects_non_numeric_values(
    field_name: str,
    value: object,
) -> None:
    """Numeric configuration fields should reject invalid types."""
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        TariffGeneratorConfig(**{field_name: value})


def test_config_rejects_reversed_rate_bounds() -> None:
    """Maximum rate must not be below minimum rate."""
    with pytest.raises(ValueError, match="maximum_rate_per_mwh"):
        TariffGeneratorConfig(
            minimum_rate_per_mwh=30_000.0,
            maximum_rate_per_mwh=20_000.0,
        )


def test_config_rejects_reversed_escalation_bounds() -> None:
    """Maximum escalation must not be below minimum escalation."""
    with pytest.raises(ValueError, match="maximum_escalation_ratio"):
        TariffGeneratorConfig(
            minimum_escalation_ratio=0.10,
            maximum_escalation_ratio=0.05,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_rate_per_mwh",
        "maximum_rate_per_mwh",
        "minimum_escalation_ratio",
        "maximum_escalation_ratio",
    ],
)
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_config_rejects_non_finite_values(
    field_name: str,
    value: float,
) -> None:
    """Numeric configuration values must be finite."""
    with pytest.raises(ValueError, match=f"{field_name} must be finite"):
        TariffGeneratorConfig(**{field_name: value})


def test_tariff_window_normalizes_code_and_category() -> None:
    """TariffWindow should normalize code and day category."""
    window = TariffWindow(
        window_code=" peak ",
        day_category=" WEEKDAY ",
        local_start_time=time(17, 0),
        local_end_time=time(22, 0),
        rate_multiplier=1.25,
    )

    assert window.window_code == "PEAK"
    assert window.day_category == "weekday"


@pytest.mark.parametrize("value", ["", " "])
def test_tariff_window_rejects_empty_code(value: str) -> None:
    """Window codes must contain text."""
    with pytest.raises(ValueError, match="window_code cannot be empty"):
        TariffWindow(
            window_code=value,
            day_category="all_days",
            local_start_time=time(0, 0),
            local_end_time=time(1, 0),
            rate_multiplier=1.0,
        )


def test_tariff_window_rejects_invalid_day_category() -> None:
    """Day category must use an approved value."""
    with pytest.raises(ValueError, match="day_category must be one of"):
        TariffWindow(
            window_code="X",
            day_category="holiday",
            local_start_time=time(0, 0),
            local_end_time=time(1, 0),
            rate_multiplier=1.0,
        )


@pytest.mark.parametrize("value", [True, "1", None])
def test_tariff_window_rejects_non_numeric_multiplier(
    value: object,
) -> None:
    """Rate multiplier must be numeric."""
    with pytest.raises(TypeError, match="rate_multiplier must be numeric"):
        TariffWindow(
            window_code="X",
            day_category="all_days",
            local_start_time=time(0, 0),
            local_end_time=time(1, 0),
            rate_multiplier=value,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_tariff_window_rejects_non_positive_multiplier(
    value: float,
) -> None:
    """Rate multiplier must be greater than zero."""
    with pytest.raises(ValueError, match="greater than zero"):
        TariffWindow(
            window_code="X",
            day_category="all_days",
            local_start_time=time(0, 0),
            local_end_time=time(1, 0),
            rate_multiplier=value,
        )


def test_tariff_window_requires_both_time_values() -> None:
    """Start and end times must be supplied together."""
    with pytest.raises(ValueError, match="must both be set"):
        TariffWindow(
            window_code="X",
            day_category="all_days",
            local_start_time=time(0, 0),
            local_end_time=None,
            rate_multiplier=1.0,
        )


def test_generate_tariffs_rejects_empty_plants() -> None:
    """At least one plant is required."""
    with pytest.raises(ValueError, match="at least one plant"):
        generate_tariffs(
            pd.DataFrame(columns=["plant_id", "currency"]),
            _time_range(),
            _config(),
        )


def test_generate_tariffs_rejects_missing_plant_id_column() -> None:
    """Plant DataFrames must include plant_id."""
    with pytest.raises(ValueError, match="must contain plant_id"):
        generate_tariffs(
            pd.DataFrame([{"currency": "PKR"}]),
            _time_range(),
            _config(),
        )


def test_generate_tariffs_rejects_duplicate_plant_ids() -> None:
    """Duplicate plant IDs must fail before generation."""
    plants = pd.DataFrame(
        [
            {"plant_id": "PLT-001", "currency": "PKR"},
            {"plant_id": "PLT-001", "currency": "PKR"},
        ]
    )

    with pytest.raises(ValueError, match="Duplicate plant_id"):
        generate_tariffs(plants, _time_range(), _config())


def test_generate_tariffs_rejects_invalid_time_range() -> None:
    """End must be greater than start."""
    invalid_range = {
        "start": datetime(2025, 1, 2, tzinfo=UTC),
        "end": datetime(2025, 1, 1, tzinfo=UTC),
    }

    with pytest.raises(ValueError, match="end must be greater than start"):
        generate_tariffs(
            _plants_frame(),
            invalid_range,
            _config(),
        )


def test_generate_tariffs_rejects_naive_time_range() -> None:
    """Time-range bounds must be timezone-aware."""
    invalid_range = {
        "start": datetime(2025, 1, 1),
        "end": datetime(2026, 1, 1),
    }

    with pytest.raises(ValueError, match="timezone-aware"):
        generate_tariffs(
            _plants_frame(),
            invalid_range,
            _config(),
        )


def test_generate_tariffs_rejects_empty_run_id() -> None:
    """generation_run_id must contain text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_tariffs(
            _plants_frame(),
            _time_range(),
            _config(),
            generation_run_id=" ",
        )


def test_generate_tariffs_rejects_duplicate_tou_codes() -> None:
    """TOU window codes must be unique."""
    windows = (
        TariffWindow(
            window_code="PEAK",
            day_category="all_days",
            local_start_time=time(0, 0),
            local_end_time=time(12, 0),
            rate_multiplier=1.0,
        ),
        TariffWindow(
            window_code="peak",
            day_category="all_days",
            local_start_time=time(12, 0),
            local_end_time=time(0, 0),
            rate_multiplier=1.0,
        ),
    )

    with pytest.raises(ValueError, match="duplicate window codes"):
        generate_tariffs(
            _plants_frame(),
            _time_range(),
            _config(flat_tariff_probability=0.0),
            tou_windows=windows,
        )
