"""Unit tests for EOIP forecasting dataset contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from eoip.forecasting.dataset.base import (
    ForecastDataset,
    ForecastTarget,
)


def _frame() -> pd.DataFrame:
    """Return a valid forecasting DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-08-17T10:00:00Z",
                    "2026-08-17T10:15:00Z",
                    "2026-08-17T10:30:00Z",
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


def _dataset() -> ForecastDataset:
    """Return a valid forecasting dataset."""
    return ForecastDataset(
        data=_frame(),
        timestamp_column="timestamp",
        target_column="active_power_kw",
        frequency="15min",
    )


class TestForecastTarget:
    """Tests for supported forecasting targets."""

    def test_active_power_target_value(self) -> None:
        assert ForecastTarget.ACTIVE_POWER_KW.value == "active_power_kw"

    def test_interval_energy_target_value(self) -> None:
        assert ForecastTarget.INTERVAL_ENERGY_KWH.value == "interval_energy_kwh"

    def test_ghi_target_value(self) -> None:
        assert ForecastTarget.GHI_WM2.value == "ghi_wm2"


class TestForecastDatasetValidation:
    """Tests for ForecastDataset validation."""

    def test_accepts_valid_dataset(self) -> None:
        dataset = _dataset()

        assert dataset.row_count == 3
        assert dataset.timestamp_column == "timestamp"
        assert dataset.target_column == "active_power_kw"
        assert dataset.frequency == "15min"

    def test_rejects_empty_dataframe(self) -> None:
        with pytest.raises(
            ValueError,
            match="Forecast dataset must not be empty.",
        ):
            ForecastDataset(
                data=pd.DataFrame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_rejects_empty_timestamp_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="timestamp_column must not be empty.",
        ):
            ForecastDataset(
                data=_frame(),
                timestamp_column=" ",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_rejects_empty_target_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            ForecastDataset(
                data=_frame(),
                timestamp_column="timestamp",
                target_column=" ",
                frequency="15min",
            )

    def test_rejects_empty_frequency(self) -> None:
        with pytest.raises(
            ValueError,
            match="frequency must not be empty.",
        ):
            ForecastDataset(
                data=_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency=" ",
            )

    def test_rejects_missing_timestamp_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing timestamp column: missing_timestamp",
        ):
            ForecastDataset(
                data=_frame(),
                timestamp_column="missing_timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_rejects_missing_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing target column: missing_target",
        ):
            ForecastDataset(
                data=_frame(),
                timestamp_column="timestamp",
                target_column="missing_target",
                frequency="15min",
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
            match=("Forecast timestamp column must contain " "datetime values."),
        ):
            ForecastDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_rejects_missing_timestamp_value(self) -> None:
        frame = _frame()
        frame.loc[1, "timestamp"] = pd.NaT

        with pytest.raises(
            ValueError,
            match=("Forecast timestamp column must not contain " "missing values."),
        ):
            ForecastDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_rejects_duplicate_timestamps(self) -> None:
        frame = _frame()
        frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"]

        with pytest.raises(
            ValueError,
            match=("Forecast timestamp column must not contain " "duplicates."),
        ):
            ForecastDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
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
            match=("Forecast target column must contain numeric values."),
        ):
            ForecastDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_rejects_missing_target_value(self) -> None:
        frame = _frame()
        frame.loc[1, "active_power_kw"] = float("nan")

        with pytest.raises(
            ValueError,
            match=("Forecast target column must not contain " "missing values."),
        ):
            ForecastDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
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
            match=("Forecast timestamps must be sorted " "in ascending order."),
        ):
            ForecastDataset(
                data=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )


class TestForecastDatasetProperties:
    """Tests for ForecastDataset properties."""

    def test_start_at(self) -> None:
        dataset = _dataset()

        assert dataset.start_at == datetime(
            2026,
            8,
            17,
            10,
            0,
            tzinfo=UTC,
        )

    def test_end_at(self) -> None:
        dataset = _dataset()

        assert dataset.end_at == datetime(
            2026,
            8,
            17,
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
