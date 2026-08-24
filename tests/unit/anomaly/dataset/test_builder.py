"""Unit tests for EOIP anomaly dataset builder."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.anomaly.dataset.builder import build_anomaly_dataset


def _frame() -> pd.DataFrame:
    """Return a valid source DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-08-18T10:30:00Z",
                "2026-08-18T10:00:00Z",
                "2026-08-18T10:15:00Z",
            ],
            "active_power_kw": [
                600.0,
                400.0,
                500.0,
            ],
            "ghi_wm2": [
                800.0,
                600.0,
                700.0,
            ],
        }
    )


class TestBuildAnomalyDataset:
    """Tests for anomaly dataset construction."""

    def test_builds_valid_dataset(self) -> None:
        dataset = build_anomaly_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        assert dataset.row_count == 3
        assert dataset.timestamp_column == "timestamp"
        assert dataset.target_column == "active_power_kw"

    def test_sorts_timestamps(self) -> None:
        dataset = build_anomaly_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        assert dataset.data["timestamp"].is_monotonic_increasing

    def test_converts_timestamp_strings_to_datetime(self) -> None:
        dataset = build_anomaly_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        assert pd.api.types.is_datetime64_any_dtype(dataset.data["timestamp"])

    def test_normalizes_timestamps_to_utc(self) -> None:
        dataset = build_anomaly_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        assert str(dataset.data["timestamp"].dt.tz) == "UTC"

    def test_converts_numeric_strings_to_numeric(self) -> None:
        frame = _frame()

        frame["active_power_kw"] = [
            "600.0",
            "400.0",
            "500.0",
        ]

        dataset = build_anomaly_dataset(
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        assert pd.api.types.is_numeric_dtype(dataset.data["active_power_kw"])

        assert dataset.data["active_power_kw"].tolist() == [
            400.0,
            500.0,
            600.0,
        ]

    def test_preserves_additional_columns(self) -> None:
        dataset = build_anomaly_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        assert "ghi_wm2" in dataset.data.columns

    def test_returns_independent_dataframe(self) -> None:
        frame = _frame()

        dataset = build_anomaly_dataset(
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
        )

        dataset.data.loc[
            0,
            "active_power_kw",
        ] = 9999.0

        assert 9999.0 not in frame["active_power_kw"].tolist()

    def test_rejects_empty_source_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Source frame must not be empty.",
        ):
            build_anomaly_dataset(
                frame=pd.DataFrame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_empty_timestamp_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="timestamp_column must not be empty.",
        ):
            build_anomaly_dataset(
                frame=_frame(),
                timestamp_column=" ",
                target_column="active_power_kw",
            )

    def test_rejects_empty_target_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            build_anomaly_dataset(
                frame=_frame(),
                timestamp_column="timestamp",
                target_column=" ",
            )

    def test_rejects_missing_timestamp_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing timestamp column: missing_timestamp",
        ):
            build_anomaly_dataset(
                frame=_frame(),
                timestamp_column="missing_timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing target column: missing_target",
        ):
            build_anomaly_dataset(
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="missing_target",
            )

    def test_rejects_invalid_timestamp_values(self) -> None:
        frame = _frame()

        frame.loc[
            1,
            "timestamp",
        ] = "not-a-date"

        with pytest.raises(
            ValueError,
            match=("Timestamp column contains invalid datetime values."),
        ):
            build_anomaly_dataset(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_non_numeric_target_values(self) -> None:
        frame = _frame()

        frame["active_power_kw"] = frame["active_power_kw"].astype(object)

        frame.loc[
            1,
            "active_power_kw",
        ] = "invalid"

        with pytest.raises(
            ValueError,
            match=("Target column contains non-numeric values."),
        ):
            build_anomaly_dataset(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_timestamp_values(self) -> None:
        frame = _frame()

        frame.loc[
            1,
            "timestamp",
        ] = None

        with pytest.raises(
            ValueError,
            match="Timestamp column contains missing values.",
        ):
            build_anomaly_dataset(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_missing_target_values(self) -> None:
        frame = _frame()

        frame.loc[
            1,
            "active_power_kw",
        ] = float("nan")

        with pytest.raises(
            ValueError,
            match="Target column contains missing values.",
        ):
            build_anomaly_dataset(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )

    def test_rejects_duplicate_timestamps(self) -> None:
        frame = _frame()

        frame.loc[
            1,
            "timestamp",
        ] = frame.loc[
            0,
            "timestamp",
        ]

        with pytest.raises(
            ValueError,
            match="Timestamp column contains duplicate values.",
        ):
            build_anomaly_dataset(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
            )
