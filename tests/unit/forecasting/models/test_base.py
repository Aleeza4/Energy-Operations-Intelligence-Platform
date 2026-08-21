"""Unit tests for EOIP forecasting model contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from eoip.forecasting.models.base import (
    ForecastPoint,
    ForecastResult,
)


def _predictions() -> pd.DataFrame:
    """Return a valid forecast prediction frame."""
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
            "prediction": [
                400.0,
                500.0,
                600.0,
            ],
        }
    )


class TestForecastPoint:
    """Tests for individual forecast points."""

    def test_stores_timestamp_and_value(self) -> None:
        timestamp = datetime(
            2026,
            8,
            18,
            10,
            0,
            tzinfo=UTC,
        )

        point = ForecastPoint(
            timestamp=timestamp,
            value=500.0,
        )

        assert point.timestamp == timestamp
        assert point.value == 500.0


class TestForecastResult:
    """Tests for standard forecast results."""

    def test_accepts_valid_result(self) -> None:
        result = ForecastResult(
            model_name="Naive",
            target_column="active_power_kw",
            predictions=_predictions(),
        )

        assert result.model_name == "Naive"
        assert result.target_column == "active_power_kw"
        assert len(result.predictions) == 3

    def test_rejects_empty_model_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="model_name must not be empty.",
        ):
            ForecastResult(
                model_name=" ",
                target_column="active_power_kw",
                predictions=_predictions(),
            )

    def test_rejects_empty_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            ForecastResult(
                model_name="Naive",
                target_column=" ",
                predictions=_predictions(),
            )

    def test_rejects_empty_predictions(self) -> None:
        with pytest.raises(
            ValueError,
            match="Forecast predictions must not be empty.",
        ):
            ForecastResult(
                model_name="Naive",
                target_column="active_power_kw",
                predictions=pd.DataFrame(),
            )

    def test_rejects_missing_timestamp_column(self) -> None:
        frame = pd.DataFrame(
            {
                "prediction": [
                    100.0,
                    200.0,
                ]
            }
        )

        with pytest.raises(
            ValueError,
            match="Forecast predictions are missing required columns",
        ):
            ForecastResult(
                model_name="Naive",
                target_column="active_power_kw",
                predictions=frame,
            )

    def test_rejects_missing_prediction_column(self) -> None:
        frame = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2026-08-18T10:00:00Z",
                        "2026-08-18T10:15:00Z",
                    ],
                    utc=True,
                )
            }
        )

        with pytest.raises(
            ValueError,
            match="Forecast predictions are missing required columns",
        ):
            ForecastResult(
                model_name="Naive",
                target_column="active_power_kw",
                predictions=frame,
            )

    def test_rejects_non_datetime_timestamps(self) -> None:
        frame = _predictions()
        frame["timestamp"] = [
            "a",
            "b",
            "c",
        ]

        with pytest.raises(
            TypeError,
            match=("Forecast prediction timestamps must contain " "datetime values."),
        ):
            ForecastResult(
                model_name="Naive",
                target_column="active_power_kw",
                predictions=frame,
            )

    def test_rejects_non_numeric_predictions(self) -> None:
        frame = _predictions()
        frame["prediction"] = [
            "low",
            "medium",
            "high",
        ]

        with pytest.raises(
            TypeError,
            match="Forecast prediction values must be numeric.",
        ):
            ForecastResult(
                model_name="Naive",
                target_column="active_power_kw",
                predictions=frame,
            )

    def test_rejects_missing_timestamp_values(self) -> None:
        frame = _predictions()
        frame.loc[1, "timestamp"] = pd.NaT

        with pytest.raises(
            ValueError,
            match=(
                "Forecast prediction timestamps must not contain " "missing values."
            ),
        ):
            ForecastResult(
                model_name="Naive",
                target_column="active_power_kw",
                predictions=frame,
            )

    def test_rejects_missing_prediction_values(self) -> None:
        frame = _predictions()
        frame.loc[1, "prediction"] = float("nan")

        with pytest.raises(
            ValueError,
            match=("Forecast prediction values must not contain " "missing values."),
        ):
            ForecastResult(
                model_name="Naive",
                target_column="active_power_kw",
                predictions=frame,
            )
