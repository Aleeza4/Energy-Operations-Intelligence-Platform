"""Focused Phase L evidence-safety tests."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from eoip.phase_l import (
    EVIDENCE_TYPE,
    calculate_data_quality,
    chronological_split,
    evidence_metadata,
    future_failure_labels,
)


def test_chronological_split_has_no_time_overlap() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=10, freq="h", tz="UTC"),
            "value": range(10),
        }
    )
    result = chronological_split(frame, timestamp_column="timestamp")
    assert result.train["timestamp"].max() < result.validation["timestamp"].min()
    assert result.validation["timestamp"].max() < result.test["timestamp"].min()
    assert list(result.train["value"]) == list(range(6))


def test_split_keeps_same_timestamp_in_one_population() -> None:
    timestamps = pd.date_range("2025-01-01", periods=5, freq="h", tz="UTC").repeat(2)
    result = chronological_split(
        pd.DataFrame({"timestamp": timestamps, "asset": ["a", "b"] * 5}),
        timestamp_column="timestamp",
    )
    sets = [
        set(part["timestamp"])
        for part in (result.train, result.validation, result.test)
    ]
    assert sets[0].isdisjoint(sets[1])
    assert sets[1].isdisjoint(sets[2])


def test_future_failure_labels_exclude_current_and_post_failure_rows() -> None:
    failure_at = datetime(2025, 1, 2, tzinfo=UTC)
    observations = pd.DataFrame(
        {
            "timestamp": [
                failure_at - timedelta(hours=12),
                failure_at,
                failure_at + timedelta(hours=1),
            ],
            "equipment_id": ["A", "A", "A"],
        }
    )
    failures = pd.DataFrame({"equipment_id": ["A"], "failed_at": [failure_at]})
    labels = future_failure_labels(
        observations,
        failures,
        timestamp_column="timestamp",
        equipment_column="equipment_id",
        failure_timestamp_column="failed_at",
        horizon=timedelta(hours=24),
    )
    assert labels.tolist() == [True, False, False]


def test_data_quality_uses_expected_slots_and_business_key_duplicates() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2025-01-01T00:00Z", "2025-01-01T00:15Z", "2025-01-01T00:15Z"]
            ),
            "asset": ["A", "A", "A"],
            "sensor": [1.0, 2.0, 2.0],
            "quality_flag": ["valid", "valid", "valid"],
        }
    )
    result = calculate_data_quality(
        frame,
        timestamp_column="timestamp",
        asset_column="asset",
        interval_minutes=15,
        numeric_ranges={"sensor": (0, 10)},
    )
    assert result["expected_slots"] == 2
    assert result["observed_unique_slots"] == 2
    assert result["duplicate_record_count"] == 1
    assert result["sensor_validity_percent"] == 100.0


def test_unavailable_sensor_validity_stays_unavailable() -> None:
    result = calculate_data_quality(
        pd.DataFrame({"timestamp": ["2025-01-01T00:00Z"], "asset": ["A"]}),
        timestamp_column="timestamp",
        asset_column="asset",
        interval_minutes=15,
    )
    assert result["sensor_validity_percent"] is None


def test_evidence_is_never_labeled_production() -> None:
    metadata = evidence_metadata(generated_at=datetime(2025, 1, 1, tzinfo=UTC))
    assert metadata["evidence_type"] == EVIDENCE_TYPE
    assert metadata["production_evidence"] == "false"


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        evidence_metadata(generated_at=datetime(2025, 1, 1))
