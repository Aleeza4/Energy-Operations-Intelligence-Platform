"""Acceptance tests for EOIP synthetic-data reproducibility."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from eoip.synthetic.config import (
    GenerationConfig,
    GenerationProfile,
    PortfolioConfig,
    TimeRangeConfig,
)
from eoip.synthetic.generator import generate_dataset
from eoip.synthetic.reproducibility import (
    ReproducibilityVerifier,
    compare_datasets,
    config_fingerprint,
    dataset_fingerprint,
    verify_different_seed,
    verify_same_seed,
)

SEED = 20260822
OTHER_SEED = 20260823


def _config(
    *,
    seed: int = SEED,
) -> GenerationConfig:
    """Create a small deterministic configuration for acceptance testing."""
    return GenerationConfig(
        profile_name=GenerationProfile.UNIT,
        seed=seed,
        time=TimeRangeConfig(
            start=datetime(
                2026,
                8,
                1,
                tzinfo=UTC,
            ),
            end=datetime(
                2026,
                8,
                2,
                tzinfo=UTC,
            ),
            interval_minutes=15,
        ),
        portfolio=PortfolioConfig(
            plant_count=1,
            aggregate_ac_capacity_min_mw=20.0,
            aggregate_ac_capacity_max_mw=25.0,
            plant_ac_capacity_min_mw=20.0,
            plant_ac_capacity_max_mw=25.0,
            inverter_count_min=1,
            inverter_count_max=1,
        ),
    )


def _assert_same_value(
    first: object,
    second: object,
) -> None:
    """Compare EOIP generated values using the correct comparison strategy."""
    if isinstance(first, pd.DataFrame) and isinstance(second, pd.DataFrame):
        pd.testing.assert_frame_equal(
            first.reset_index(drop=True),
            second.reset_index(drop=True),
            check_dtype=True,
            check_like=False,
        )
        return

    if isinstance(first, pd.Series) and isinstance(second, pd.Series):
        pd.testing.assert_series_equal(
            first.reset_index(drop=True),
            second.reset_index(drop=True),
            check_dtype=True,
            check_names=True,
        )
        return

    assert first == second


def test_same_configuration_has_stable_fingerprint() -> None:
    """Identical generation configurations should have identical fingerprints."""
    first = _config()
    second = _config()

    assert config_fingerprint(first) == config_fingerprint(second)


def test_different_seed_changes_configuration_fingerprint() -> None:
    """Changing the seed should change the configuration fingerprint."""
    first = _config(
        seed=SEED,
    )
    second = _config(
        seed=OTHER_SEED,
    )

    assert config_fingerprint(first) != config_fingerprint(second)


def test_same_seed_produces_identical_dataset_fingerprint() -> None:
    """Repeated generation with the same seed should be deterministic."""
    config = _config()

    first = generate_dataset(config)
    second = generate_dataset(config)

    assert dataset_fingerprint(first) == dataset_fingerprint(second)


def test_different_seed_changes_dataset_fingerprint() -> None:
    """Different seeds should produce different synthetic datasets."""
    first = generate_dataset(
        _config(
            seed=SEED,
        )
    )
    second = generate_dataset(
        _config(
            seed=OTHER_SEED,
        )
    )

    assert dataset_fingerprint(first) != dataset_fingerprint(second)


def test_same_seed_preserves_core_generated_tables() -> None:
    """Core generated datasets should remain identical for the same seed."""
    config = _config()

    first = generate_dataset(config)
    second = generate_dataset(config)

    _assert_same_value(
        first.plants,
        second.plants,
    )
    _assert_same_value(
        first.equipment,
        second.equipment,
    )
    _assert_same_value(
        first.revenue_meters,
        second.revenue_meters,
    )
    _assert_same_value(
        first.weather,
        second.weather,
    )
    _assert_same_value(
        first.inverter_scada,
        second.inverter_scada,
    )
    _assert_same_value(
        first.plant_scada,
        second.plant_scada,
    )
    _assert_same_value(
        first.ground_truth_events,
        second.ground_truth_events,
    )
    _assert_same_value(
        first.alarms,
        second.alarms,
    )
    _assert_same_value(
        first.incidents,
        second.incidents,
    )
    _assert_same_value(
        first.work_orders,
        second.work_orders,
    )
    _assert_same_value(
        first.tariffs,
        second.tariffs,
    )
    _assert_same_value(
        first.budgets,
        second.budgets,
    )


def test_compare_datasets_reports_same_seed_comparison() -> None:
    """Dataset comparison should support two same-seed datasets."""
    config = _config()

    first = generate_dataset(config)
    second = generate_dataset(config)

    comparisons = compare_datasets(
        first,
        second,
    )

    assert isinstance(comparisons, tuple)
    assert comparisons


def test_compare_datasets_reports_different_seed_comparison() -> None:
    """Dataset comparison should support datasets generated from different seeds."""
    first = generate_dataset(
        _config(
            seed=SEED,
        )
    )
    second = generate_dataset(
        _config(
            seed=OTHER_SEED,
        )
    )

    comparisons = compare_datasets(
        first,
        second,
    )

    assert isinstance(comparisons, tuple)
    assert comparisons


def test_same_seed_verification_returns_report() -> None:
    """The public same-seed verification helper should return a report."""
    report = verify_same_seed(
        _config(),
        run_validation=True,
    )

    assert report is not None
    assert report.config_fingerprint


def test_different_seed_verification_returns_report() -> None:
    """The public different-seed verification helper should return a report."""
    report = verify_different_seed(
        _config(),
        OTHER_SEED,
        run_validation=True,
    )

    assert report is not None
    assert report.config_fingerprint


def test_reproducibility_verifier_same_seed_execution() -> None:
    """ReproducibilityVerifier should execute same-seed verification."""
    verifier = ReproducibilityVerifier(_config())

    report = verifier.verify_same_seed(
        run_validation=True,
    )

    assert report is not None
    assert report.config_fingerprint


def test_reproducibility_verifier_different_seed_execution() -> None:
    """ReproducibilityVerifier should execute different-seed verification."""
    verifier = ReproducibilityVerifier(_config())

    report = verifier.verify_different_seed(
        OTHER_SEED,
        run_validation=True,
    )

    assert report is not None
    assert report.config_fingerprint
