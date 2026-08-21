"""Unit tests for EOIP anomaly dataset contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from eoip.anomaly.dataset.base import (
    AnomalyDataset,
    AnomalyTarget,
)


def _frame() -> pd.DataFrame:
    """Return a valid anomaly detection DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-08-18T10:00:00Z",
                    "2026-08-18T10:15:00Z",
                    "2026-08-18T10:30:00Z",
                ],
                utc=True,
            ),
            "active_power_kw": [
                400.0,
                500.0,
                600.0,
            ],
        }
    )


def _dataset() -> AnomalyDataset:
    """Return a valid anomaly dataset."""
    return AnomalyDataset(
        data=_frame(),
        timestamp_column="timestamp",
        target_column="active_power_kw",
    )


class TestAnomalyTarget:
    """Tests for supported anomaly targets."""

    def test_active_power_target(self) -> None:
        assert AnomalyTarget.ACTIVE_POWER_KW.value == "active_power_kw"

    def test_interval_energy_target(self) -> None:
        assert AnomalyTarget.INTERVAL_ENERGY_KWH.value == "interval_energy_kwh"

    def test_performance_ratio_target(self) -> None:
        assert AnomalyTarget.PERFORMANCE_RATIO.value == "performance_ratio"

    def test_residual_target(self) -> None:
        assert AnomalyTarget.RESIDUAL.value == "residual"


class TestAnomalyDatasetValidation:
    """Tests for anomaly dataset validation."""

    def test_accepts_valid_dataset(self) -> None:
        dataset = _dataset()

        assert dataset.row_count == 3
        assert dataset.timestamp_column == "timestamp"
        assert dataset.target_column == "active_power_kw"

    def test_rejects_empty_dataframe(self) -> None:
        with pytest.raises(
            ValueError,
            match="Anomaly dataset must not be empty.",
        ):
            AnomalyDataset(
                data=pd.DataFrame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_empty_timestamp_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="timestamp_column must not be empty.",
        ):
            AnomalyDataset(
                data=_frame(),
                timestamp_column=" ",
                target_column="active_power_kw",
            )

    def test_rejects_empty_target_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            AnomalyDataset(
                data=_frame(),
                timestamp_column="timestamp",
                target_column=" ",
            )

    def test_rejects_missing_timestamp_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing timestamp column: missing_timestamp",
        ):
            AnomalyDataset(
                data=_frame(),
                timestamp_column="missing_timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing target column: missing_target",
        ):
            AnomalyDataset(
                data=_frame(),
                timestamp_column="timestamp",
                target_column="missing_target",
            )

    def test_rejects_non_datetime_timestamp_column(self) -> None:
        frame = _frame()
        frame["timestamp"] = [
            "a",
            "b",
            "c",
        ]

        with pytest.raises(
            TypeError,
            match=("Anomaly timestamp column must contain datetime values."),
        ):
            AnomalyDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_timestamp_value(self) -> None:
        frame = _frame()
        frame.loc[1, "timestamp"] = pd.NaT

        with pytest.raises(
            ValueError,
            match=("Anomaly timestamp column must not contain " "missing values."),
        ):
            AnomalyDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_duplicate_timestamps(self) -> None:
        frame = _frame()
        frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"]

        with pytest.raises(
            ValueError,
            match=("Anomaly timestamp column must not contain duplicates."),
        ):
            AnomalyDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_unsorted_timestamps(self) -> None:
        frame = (
            _frame()
            .iloc[
                [
                    1,
                    0,
                    2,
                ]
            ]
            .reset_index(drop=True)
        )

        with pytest.raises(
            ValueError,
            match=("Anomaly timestamps must be sorted in ascending order."),
        ):
            AnomalyDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_non_numeric_target(self) -> None:
        frame = _frame()
        frame["active_power_kw"] = [
            "low",
            "medium",
            "high",
        ]

        with pytest.raises(
            TypeError,
            match=("Anomaly target column must contain numeric values."),
        ):
            AnomalyDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_target_value(self) -> None:
        frame = _frame()
        frame.loc[1, "active_power_kw"] = float("nan")

        with pytest.raises(
            ValueError,
            match=("Anomaly target column must not contain missing values."),
        ):
            AnomalyDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )


class TestAnomalyDatasetProperties:
    """Tests for anomaly dataset properties."""

    def test_start_at(self) -> None:
        dataset = _dataset()

        assert dataset.start_at == datetime(
            2026,
            8,
            18,
            10,
            0,
            tzinfo=UTC,
        )

    def test_end_at(self) -> None:
        dataset = _dataset()

        assert dataset.end_at == datetime(
            2026,
            8,
            18,
            10,
            30,
            tzinfo=UTC,
        )

    def test_row_count(self) -> None:
        dataset = _dataset()

        assert dataset.row_count == 3

    def test_copy_frame_returns_independent_dataframe(self) -> None:
        dataset = _dataset()

        copied = dataset.copy_frame()

        assert copied.equals(dataset.data)
        assert copied is not dataset.data

        copied.loc[0, "active_power_kw"] = 9999.0

        assert dataset.data.loc[0, "active_power_kw"] == 400.0
