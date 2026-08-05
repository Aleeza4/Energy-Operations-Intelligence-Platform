"""
Unit tests for the EOIP Phase 2 monthly budget generator.

These tests verify deterministic plant-month budget generation, tariff
coverage, expected-energy overrides, fallback planning calculations,
configuration validation, stable identifiers, schema order, and generated
DataFrame integrity.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest

from eoip.synthetic.generators.budgets import (
    BudgetGeneratorConfig,
    generate_budgets,
)


def _plants_frame() -> pd.DataFrame:
    """Return compact plant master data for budget tests."""
    return pd.DataFrame(
        [
            {
                "plant_id": "PLT-001",
                "ac_capacity_mw": 50.0,
                "currency": "PKR",
                "commissioning_date": date(2020, 1, 1),
                "target_performance_ratio": 0.82,
                "annual_degradation_rate": 0.005,
            },
            {
                "plant_id": "PLT-002",
                "ac_capacity_mw": 75.0,
                "currency": "USD",
                "commissioning_date": date(2018, 6, 1),
                "target_performance_ratio": 0.80,
                "annual_degradation_rate": 0.006,
            },
        ]
    )


def _month_windows() -> list[date]:
    """Return three consecutive month starts."""
    return [
        date(2025, 1, 1),
        date(2025, 2, 1),
        date(2025, 3, 1),
    ]


def _tariffs_frame() -> pd.DataFrame:
    """Return complete flat-rate tariff coverage for both plants."""
    return pd.DataFrame(
        [
            {
                "plant_id": "PLT-001",
                "effective_start_date": date(2025, 1, 1),
                "effective_end_date": date(2025, 12, 31),
                "energy_rate_per_mwh": 20_000.0,
            },
            {
                "plant_id": "PLT-002",
                "effective_start_date": date(2025, 1, 1),
                "effective_end_date": date(2025, 12, 31),
                "energy_rate_per_mwh": 25_000.0,
            },
        ]
    )


def _config(**overrides: Any) -> BudgetGeneratorConfig:
    """Return deterministic budget configuration with optional overrides."""
    data: dict[str, Any] = {
        "random_seed": 20250201,
        "default_currency": "PKR",
        "default_target_performance_ratio": 0.82,
        "default_target_availability_ratio": 0.985,
        "minimum_capacity_factor": 0.20,
        "maximum_capacity_factor": 0.20,
        "annual_opex_per_mw": 2_400_000.0,
        "annual_planned_maintenance_per_mw": 480_000.0,
        "age_opex_escalation_per_year": 0.0,
        "monthly_energy_uncertainty_ratio": 0.0,
        "monthly_cost_uncertainty_ratio": 0.0,
        "basis_version": "TEST-BASIS-1.0",
        "schema_version": "1.0.0",
    }
    data.update(overrides)
    return BudgetGeneratorConfig(**data)


def _expected_energy_frame() -> pd.DataFrame:
    """Return explicit monthly expected energy for both plants."""
    rows: list[dict[str, object]] = []

    for plant_id, base in (("PLT-001", 10_000.0), ("PLT-002", 20_000.0)):
        for offset, month_start in enumerate(_month_windows()):
            rows.append(
                {
                    "plant_id": plant_id,
                    "month_start": month_start,
                    "expected_energy_mwh": base + offset * 100.0,
                }
            )

    return pd.DataFrame(rows)


def test_generate_budgets_returns_expected_dataframe() -> None:
    """Generation should return one row per plant-month."""
    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(),
        generation_run_id="RUN-TEST",
    )

    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 6
    assert list(frame["plant_id"]) == [
        "PLT-001",
        "PLT-001",
        "PLT-001",
        "PLT-002",
        "PLT-002",
        "PLT-002",
    ]


def test_budget_ids_follow_canonical_format() -> None:
    """Budget IDs should combine plant ID, year, and month."""
    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(),
    )

    assert list(frame["budget_id"]) == [
        "PLT-001-2025-01",
        "PLT-001-2025-02",
        "PLT-001-2025-03",
        "PLT-002-2025-01",
        "PLT-002-2025-02",
        "PLT-002-2025-03",
    ]


def test_output_column_order_is_stable() -> None:
    """Generated columns should match the Phase 2 budget contract."""
    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(),
    )

    assert tuple(frame.columns) == (
        "budget_id",
        "plant_id",
        "budget_year",
        "budget_month",
        "budget_energy_mwh",
        "budget_revenue",
        "target_performance_ratio",
        "target_technical_availability_ratio",
        "budget_opex",
        "budget_planned_maintenance",
        "currency",
        "basis_version",
        "generation_run_id",
        "schema_version",
    )


def test_generation_is_deterministic() -> None:
    """Identical inputs should generate identical logical rows."""
    first = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(),
    )
    second = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(),
    )

    pd.testing.assert_frame_equal(first, second)


def test_different_seed_changes_fallback_energy() -> None:
    """Different seeds should change fallback expected energy."""
    first = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(
            random_seed=1,
            minimum_capacity_factor=0.17,
            maximum_capacity_factor=0.27,
            monthly_energy_uncertainty_ratio=0.03,
        ),
    )
    second = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(
            random_seed=2,
            minimum_capacity_factor=0.17,
            maximum_capacity_factor=0.27,
            monthly_energy_uncertainty_ratio=0.03,
        ),
    )

    assert not first.equals(second)


def test_expected_energy_override_is_used() -> None:
    """Explicit expected-energy input should override fallback estimation."""
    frame = generate_budgets(
        _plants_frame(),
        _expected_energy_frame(),
        _tariffs_frame(),
        _month_windows(),
        _config(),
    )

    plt_001 = frame[frame["plant_id"] == "PLT-001"].reset_index(drop=True)
    assert list(plt_001["budget_energy_mwh"]) == [
        10_000.0,
        10_100.0,
        10_200.0,
    ]


def test_revenue_uses_tariff_reference_rate() -> None:
    """Budget revenue should equal energy multiplied by tariff rate."""
    frame = generate_budgets(
        _plants_frame(),
        _expected_energy_frame(),
        _tariffs_frame(),
        _month_windows(),
        _config(),
    )

    january_plant_one = frame.loc[
        (frame["plant_id"] == "PLT-001") & (frame["budget_month"] == 1)
    ].iloc[0]

    january_plant_two = frame.loc[
        (frame["plant_id"] == "PLT-002") & (frame["budget_month"] == 1)
    ].iloc[0]

    assert january_plant_one["budget_revenue"] == 200_000_000.0
    assert january_plant_two["budget_revenue"] == 500_000_000.0


def test_monthly_opex_uses_capacity_and_annual_rate() -> None:
    """Monthly Opex should scale with plant AC capacity."""
    frame = generate_budgets(
        _plants_frame(),
        _expected_energy_frame(),
        _tariffs_frame(),
        _month_windows()[:1],
        _config(),
    )

    plant_one = frame.loc[frame["plant_id"] == "PLT-001"].iloc[0]
    plant_two = frame.loc[frame["plant_id"] == "PLT-002"].iloc[0]

    assert plant_one["budget_opex"] == 10_000_000.0
    assert plant_two["budget_opex"] == 15_000_000.0


def test_monthly_maintenance_budget_scales_with_capacity() -> None:
    """Planned maintenance budget should use the annual per-MW rate."""
    frame = generate_budgets(
        _plants_frame(),
        _expected_energy_frame(),
        _tariffs_frame(),
        _month_windows()[:1],
        _config(),
    )

    plant_one = frame.loc[frame["plant_id"] == "PLT-001"].iloc[0]
    plant_two = frame.loc[frame["plant_id"] == "PLT-002"].iloc[0]

    assert plant_one["budget_planned_maintenance"] == 2_000_000.0
    assert plant_two["budget_planned_maintenance"] == 3_000_000.0


def test_currency_comes_from_plant_master_data() -> None:
    """Plant currency should be preserved in budget rows."""
    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(),
    )

    assert set(frame.loc[frame["plant_id"] == "PLT-001", "currency"]) == {"PKR"}
    assert set(frame.loc[frame["plant_id"] == "PLT-002", "currency"]) == {"USD"}


def test_missing_currency_uses_default() -> None:
    """Missing plant currency should fall back to configuration."""
    plants = _plants_frame().copy()
    plants["currency"] = None

    frame = generate_budgets(
        plants,
        None,
        _tariffs_frame(),
        _month_windows()[:1],
        _config(default_currency="eur"),
    )

    assert set(frame["currency"]) == {"EUR"}


def test_audit_columns_use_supplied_values() -> None:
    """Run ID, schema version, and basis version should be preserved."""
    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows()[:1],
        _config(
            basis_version="BASIS-X",
            schema_version="2.0.0",
        ),
        generation_run_id="RUN-ABC",
    )

    assert set(frame["basis_version"]) == {"BASIS-X"}
    assert set(frame["schema_version"]) == {"2.0.0"}
    assert set(frame["generation_run_id"]) == {"RUN-ABC"}


def test_dataframe_month_windows_are_supported() -> None:
    """Month-window DataFrames should be normalized."""
    month_frame = pd.DataFrame(
        {
            "month_start": [
                datetime(2025, 1, 15, tzinfo=UTC),
                datetime(2025, 2, 28, tzinfo=UTC),
            ]
        }
    )

    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        month_frame,
        _config(),
    )

    assert set(frame["budget_month"]) == {1, 2}


def test_month_window_objects_with_start_are_supported() -> None:
    """Objects exposing start should be accepted."""
    windows = [
        SimpleNamespace(start=datetime(2025, 1, 1, tzinfo=UTC)),
        SimpleNamespace(start=datetime(2025, 2, 1, tzinfo=UTC)),
    ]

    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        windows,
        _config(),
    )

    assert len(frame) == 4


def test_duplicate_month_windows_are_deduplicated() -> None:
    """Repeated dates in the same month should create one budget month."""
    windows = [
        date(2025, 1, 1),
        date(2025, 1, 15),
        date(2025, 2, 1),
    ]

    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        windows,
        _config(),
    )

    assert len(frame) == 4


def test_expected_energy_can_use_timestamp_column() -> None:
    """Expected-energy input may use timestamp_utc."""
    expected = pd.DataFrame(
        [
            {
                "plant_id": "PLT-001",
                "timestamp_utc": datetime(2025, 1, 15, tzinfo=UTC),
                "energy_mwh": 4_000.0,
            },
            {
                "plant_id": "PLT-001",
                "timestamp_utc": datetime(2025, 1, 20, tzinfo=UTC),
                "energy_mwh": 6_000.0,
            },
            {
                "plant_id": "PLT-002",
                "timestamp_utc": datetime(2025, 1, 10, tzinfo=UTC),
                "energy_mwh": 20_000.0,
            },
        ]
    )

    frame = generate_budgets(
        _plants_frame(),
        expected,
        _tariffs_frame(),
        [date(2025, 1, 1)],
        _config(),
    )

    plant_one = frame.loc[frame["plant_id"] == "PLT-001"].iloc[0]
    assert plant_one["budget_energy_mwh"] == 10_000.0


def test_tou_tariffs_use_average_reference_rate() -> None:
    """Monthly revenue planning should average applicable TOU rates."""
    tariffs = pd.DataFrame(
        [
            {
                "plant_id": "PLT-001",
                "effective_start_date": date(2025, 1, 1),
                "effective_end_date": date(2025, 12, 31),
                "energy_rate_per_mwh": 10_000.0,
            },
            {
                "plant_id": "PLT-001",
                "effective_start_date": date(2025, 1, 1),
                "effective_end_date": date(2025, 12, 31),
                "energy_rate_per_mwh": 30_000.0,
            },
            {
                "plant_id": "PLT-002",
                "effective_start_date": date(2025, 1, 1),
                "effective_end_date": date(2025, 12, 31),
                "energy_rate_per_mwh": 25_000.0,
            },
        ]
    )

    frame = generate_budgets(
        _plants_frame(),
        _expected_energy_frame(),
        tariffs,
        [date(2025, 1, 1)],
        _config(),
    )

    plant_one = frame.loc[frame["plant_id"] == "PLT-001"].iloc[0]
    assert plant_one["budget_revenue"] == 200_000_000.0


def test_primary_key_is_unique() -> None:
    """Every budget row should have a unique budget ID."""
    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(),
    )

    assert frame["budget_id"].is_unique


def test_generated_numeric_values_are_non_negative() -> None:
    """All planning amounts should be non-negative."""
    frame = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(),
    )

    columns = [
        "budget_energy_mwh",
        "budget_revenue",
        "budget_opex",
        "budget_planned_maintenance",
    ]

    assert (frame[columns] >= 0).all().all()


def test_config_normalizes_text_fields() -> None:
    """Configuration text values should be normalized."""
    config = BudgetGeneratorConfig(
        default_currency=" pkr ",
        basis_version=" BASIS-1 ",
        schema_version=" 1.0.0 ",
    )

    assert config.default_currency == "PKR"
    assert config.basis_version == "BASIS-1"
    assert config.schema_version == "1.0.0"


def test_config_is_immutable() -> None:
    """BudgetGeneratorConfig should be frozen."""
    config = BudgetGeneratorConfig()

    with pytest.raises(FrozenInstanceError):
        config.random_seed = 1  # type: ignore[misc]


@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_config_rejects_invalid_seed_type(value: object) -> None:
    """random_seed must be an integer excluding booleans."""
    with pytest.raises(TypeError, match="random_seed must be an integer"):
        BudgetGeneratorConfig(random_seed=value)  # type: ignore[arg-type]


def test_config_rejects_negative_seed() -> None:
    """random_seed must be non-negative."""
    with pytest.raises(ValueError, match="random_seed must be non-negative"):
        BudgetGeneratorConfig(random_seed=-1)


@pytest.mark.parametrize("value", ["", "US", "USDD", "1PK"])
def test_config_rejects_invalid_currency(value: str) -> None:
    """Default currency must be a three-letter alphabetic code."""
    with pytest.raises(ValueError, match="three-letter"):
        BudgetGeneratorConfig(default_currency=value)


@pytest.mark.parametrize(
    "field_name",
    [
        "default_target_performance_ratio",
        "default_target_availability_ratio",
        "minimum_capacity_factor",
        "maximum_capacity_factor",
        "age_opex_escalation_per_year",
        "monthly_energy_uncertainty_ratio",
        "monthly_cost_uncertainty_ratio",
        "annual_opex_per_mw",
        "annual_planned_maintenance_per_mw",
    ],
)
@pytest.mark.parametrize("value", [True, "1", None])
def test_config_rejects_non_numeric_values(
    field_name: str,
    value: object,
) -> None:
    """Numeric configuration fields should reject invalid types."""
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        BudgetGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "default_target_performance_ratio",
        "default_target_availability_ratio",
        "minimum_capacity_factor",
        "maximum_capacity_factor",
        "age_opex_escalation_per_year",
        "monthly_energy_uncertainty_ratio",
        "monthly_cost_uncertainty_ratio",
        "annual_opex_per_mw",
        "annual_planned_maintenance_per_mw",
    ],
)
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_config_rejects_non_finite_values(
    field_name: str,
    value: float,
) -> None:
    """Numeric configuration values must be finite."""
    with pytest.raises(ValueError, match=f"{field_name} must be finite"):
        BudgetGeneratorConfig(**{field_name: value})


def test_config_rejects_reversed_capacity_factor_bounds() -> None:
    """Maximum capacity factor must not be below minimum."""
    with pytest.raises(ValueError, match="maximum_capacity_factor"):
        BudgetGeneratorConfig(
            minimum_capacity_factor=0.30,
            maximum_capacity_factor=0.20,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_capacity_factor",
        "maximum_capacity_factor",
        "age_opex_escalation_per_year",
        "monthly_energy_uncertainty_ratio",
        "monthly_cost_uncertainty_ratio",
    ],
)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_config_rejects_ratio_outside_bounds(
    field_name: str,
    value: float,
) -> None:
    """Bounded ratios must remain between zero and one."""
    with pytest.raises(ValueError):
        BudgetGeneratorConfig(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "annual_opex_per_mw",
        "annual_planned_maintenance_per_mw",
    ],
)
def test_config_rejects_negative_cost_rates(field_name: str) -> None:
    """Annual cost rates must be non-negative."""
    with pytest.raises(ValueError, match="must be non-negative"):
        BudgetGeneratorConfig(**{field_name: -1.0})


def test_generate_budgets_rejects_empty_plants() -> None:
    """At least one plant is required."""
    with pytest.raises(ValueError, match="at least one plant"):
        generate_budgets(
            pd.DataFrame(
                columns=[
                    "plant_id",
                    "ac_capacity_mw",
                ]
            ),
            None,
            _tariffs_frame(),
            _month_windows(),
            _config(),
        )


def test_generate_budgets_rejects_empty_months() -> None:
    """At least one month is required."""
    with pytest.raises(ValueError, match="at least one month"):
        generate_budgets(
            _plants_frame(),
            None,
            _tariffs_frame(),
            [],
            _config(),
        )


def test_generate_budgets_rejects_empty_run_id() -> None:
    """generation_run_id must contain text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_budgets(
            _plants_frame(),
            None,
            _tariffs_frame(),
            _month_windows(),
            _config(),
            generation_run_id=" ",
        )


def test_generate_budgets_rejects_duplicate_plant_ids() -> None:
    """Duplicate plant IDs must fail before generation."""
    plants = pd.concat(
        [_plants_frame().iloc[:1], _plants_frame().iloc[:1]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="Duplicate plant_id"):
        generate_budgets(
            plants,
            None,
            _tariffs_frame(),
            _month_windows(),
            _config(),
        )


def test_generate_budgets_rejects_missing_tariff_coverage() -> None:
    """Every plant-month must have applicable tariff coverage."""
    tariffs = _tariffs_frame()
    tariffs = tariffs[tariffs["plant_id"] == "PLT-001"]

    with pytest.raises(ValueError, match="No tariff coverage found"):
        generate_budgets(
            _plants_frame(),
            None,
            tariffs,
            _month_windows(),
            _config(),
        )


def test_generate_budgets_rejects_missing_tariff_columns() -> None:
    """Tariff input must contain the required coverage columns."""
    with pytest.raises(ValueError, match="missing required columns"):
        generate_budgets(
            _plants_frame(),
            None,
            pd.DataFrame([{"plant_id": "PLT-001"}]),
            _month_windows(),
            _config(),
        )


def test_generate_budgets_rejects_negative_tariff_rate() -> None:
    """Tariff rates must be non-negative."""
    tariffs = _tariffs_frame()
    tariffs.loc[0, "energy_rate_per_mwh"] = -1.0

    with pytest.raises(ValueError, match="Tariff rates"):
        generate_budgets(
            _plants_frame(),
            None,
            tariffs,
            _month_windows(),
            _config(),
        )


def test_generate_budgets_rejects_negative_expected_energy() -> None:
    """Expected-energy input must be non-negative."""
    expected = _expected_energy_frame()
    expected.loc[0, "expected_energy_mwh"] = -1.0

    with pytest.raises(ValueError, match="Expected energy"):
        generate_budgets(
            _plants_frame(),
            expected,
            _tariffs_frame(),
            _month_windows(),
            _config(),
        )


def test_generate_budgets_rejects_missing_expected_energy_columns() -> None:
    """Expected-energy input must include plant, month, and energy columns."""
    with pytest.raises(ValueError, match="must contain expected_energy_mwh"):
        generate_budgets(
            _plants_frame(),
            pd.DataFrame(
                [
                    {
                        "plant_id": "PLT-001",
                        "month_start": date(2025, 1, 1),
                    }
                ]
            ),
            _tariffs_frame(),
            _month_windows(),
            _config(),
        )


class _FakeRandomContext:
    """Simple deterministic RandomContext test double."""

    def generator(
        self,
        name: str,
        entity_id: str | None = None,
    ) -> np.random.Generator:
        assert name == "budgets"
        assert entity_id is not None
        entropy = sum(ord(character) for character in entity_id)
        return np.random.default_rng(entropy)


def test_random_context_overrides_config_seed() -> None:
    """An explicit random context should control random generation."""
    context = _FakeRandomContext()

    first = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(random_seed=1),
        random_context=context,
    )
    second = generate_budgets(
        _plants_frame(),
        None,
        _tariffs_frame(),
        _month_windows(),
        _config(random_seed=999),
        random_context=context,
    )

    pd.testing.assert_frame_equal(first, second)
