"""Unit tests for EOIP forecasting dataset builder."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.forecasting.dataset.builder import build_forecast_dataset


def _frame() -> pd.DataFrame:
    """Return a valid source forecasting DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-08-17T10:30:00Z",
                "2026-08-17T10:00:00Z",
                "2026-08-17T10:15:00Z",
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
            "ambient_temperature_c": [
                30.0,
                28.0,
                29.0,
            ],
        }
    )


class TestBuildForecastDataset:
    """Tests for forecasting dataset construction."""

    def test_builds_valid_forecast_dataset(self) -> None:
        dataset = build_forecast_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
            frequency="15min",
        )

        assert dataset.row_count == 3
        assert dataset.timestamp_column == "timestamp"
        assert dataset.target_column == "active_power_kw"
        assert dataset.frequency == "15min"

    def test_sorts_timestamps(self) -> None:
        dataset = build_forecast_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
            frequency="15min",
        )

        timestamps = dataset.data["timestamp"]

        assert timestamps.is_monotonic_increasing

    def test_converts_timestamp_strings_to_datetime(self) -> None:
        dataset = build_forecast_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
            frequency="15min",
        )

        assert pd.api.types.is_datetime64_any_dtype(dataset.data["timestamp"])

    def test_retains_requested_feature_columns(self) -> None:
        dataset = build_forecast_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
            frequency="15min",
            feature_columns=[
                "ghi_wm2",
                "ambient_temperature_c",
            ],
        )

        assert list(dataset.data.columns) == [
            "timestamp",
            "active_power_kw",
            "ghi_wm2",
            "ambient_temperature_c",
        ]

    def test_does_not_duplicate_target_when_used_as_feature(
        self,
    ) -> None:
        dataset = build_forecast_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
            frequency="15min",
            feature_columns=[
                "active_power_kw",
                "ghi_wm2",
            ],
        )

        assert list(dataset.data.columns) == [
            "timestamp",
            "active_power_kw",
            "ghi_wm2",
        ]

    def test_returns_independent_dataframe(self) -> None:
        frame = _frame()

        dataset = build_forecast_dataset(
            frame=frame,
            timestamp_column="timestamp",
            target_column="active_power_kw",
            frequency="15min",
        )

        dataset.data.loc[0, "active_power_kw"] = 9999.0

        assert 9999.0 not in frame["active_power_kw"].tolist()

    def test_rejects_empty_source_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Source forecasting frame must not be empty.",
        ):
            build_forecast_dataset(
                frame=pd.DataFrame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_rejects_missing_timestamp_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Forecast source frame is missing required columns",
        ):
            build_forecast_dataset(
                frame=_frame(),
                timestamp_column="missing_timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_rejects_missing_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Forecast source frame is missing required columns",
        ):
            build_forecast_dataset(
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="missing_target",
                frequency="15min",
            )

    def test_rejects_missing_feature_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Forecast source frame is missing required columns",
        ):
            build_forecast_dataset(
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
                feature_columns=[
                    "missing_feature",
                ],
            )

    def test_error_lists_missing_columns(self) -> None:
        with pytest.raises(
            ValueError,
            match="missing_feature",
        ):
            build_forecast_dataset(
                frame=_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
                feature_columns=[
                    "missing_feature",
                ],
            )

    def test_rejects_unconvertible_timestamp_values(self) -> None:
        frame = _frame()
        frame.loc[1, "timestamp"] = "not-a-date"

        with pytest.raises(
            TypeError,
            match=(
                "Forecast timestamp column could not be converted "
                "to datetime values."
            ),
        ):
            build_forecast_dataset(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_rejects_duplicate_timestamps(self) -> None:
        frame = _frame()
        frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"]

        with pytest.raises(
            ValueError,
            match=("Forecast source frame contains duplicate timestamps."),
        ):
            build_forecast_dataset(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_propagates_missing_target_validation(self) -> None:
        frame = _frame()
        frame.loc[1, "active_power_kw"] = float("nan")

        with pytest.raises(
            ValueError,
            match=("Forecast target column must not contain " "missing values."),
        ):
            build_forecast_dataset(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )

    def test_propagates_non_numeric_target_validation(self) -> None:
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
            build_forecast_dataset(
                frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                frequency="15min",
            )
