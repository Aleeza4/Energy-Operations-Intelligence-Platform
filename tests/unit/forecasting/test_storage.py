"""Unit tests for EOIP forecast storage utilities."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from eoip.forecasting.models.base import ForecastResult
from eoip.forecasting.storage import (
    StoredForecast,
    validate_forecast_for_storage,
)


def _forecast() -> ForecastResult:
    """Return a valid forecast result."""
    return ForecastResult(
        model_name="Naive",
        target_column="active_power_kw",
        predictions=pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2026-08-18T10:00:00Z",
                        "2026-08-18T10:15:00Z",
                    ],
                    utc=True,
                ),
                "prediction": [
                    500.0,
                    510.0,
                ],
            }
        ),
    )


class TestStoredForecast:
    """Tests for stored forecast metadata."""

    def test_accepts_valid_metadata(self) -> None:
        generated_at = datetime(
            2026,
            8,
            18,
            10,
            0,
            tzinfo=UTC,
        )

        result = StoredForecast(
            forecast_id="forecast-001",
            model_name="Naive",
            target_column="active_power_kw",
            generated_at=generated_at,
            row_count=2,
        )

        assert result.forecast_id == "forecast-001"
        assert result.model_name == "Naive"
        assert result.target_column == "active_power_kw"
        assert result.generated_at == generated_at
        assert result.row_count == 2

    def test_rejects_empty_forecast_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="forecast_id must not be empty.",
        ):
            StoredForecast(
                forecast_id=" ",
                model_name="Naive",
                target_column="active_power_kw",
                generated_at=datetime(
                    2026,
                    8,
                    18,
                    10,
                    0,
                    tzinfo=UTC,
                ),
                row_count=2,
            )

    def test_rejects_empty_model_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="model_name must not be empty.",
        ):
            StoredForecast(
                forecast_id="forecast-001",
                model_name=" ",
                target_column="active_power_kw",
                generated_at=datetime(
                    2026,
                    8,
                    18,
                    10,
                    0,
                    tzinfo=UTC,
                ),
                row_count=2,
            )

    def test_rejects_empty_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            StoredForecast(
                forecast_id="forecast-001",
                model_name="Naive",
                target_column=" ",
                generated_at=datetime(
                    2026,
                    8,
                    18,
                    10,
                    0,
                    tzinfo=UTC,
                ),
                row_count=2,
            )

    def test_rejects_naive_generated_at(self) -> None:
        with pytest.raises(
            ValueError,
            match="generated_at must be timezone-aware.",
        ):
            StoredForecast(
                forecast_id="forecast-001",
                model_name="Naive",
                target_column="active_power_kw",
                generated_at=datetime(
                    2026,
                    8,
                    18,
                    10,
                    0,
                ),
                row_count=2,
            )

    @pytest.mark.parametrize(
        "row_count",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_row_count(
        self,
        row_count: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="row_count must be greater than zero.",
        ):
            StoredForecast(
                forecast_id="forecast-001",
                model_name="Naive",
                target_column="active_power_kw",
                generated_at=datetime(
                    2026,
                    8,
                    18,
                    10,
                    0,
                    tzinfo=UTC,
                ),
                row_count=row_count,
            )


class TestValidateForecastForStorage:
    """Tests for forecast persistence validation."""

    def test_accepts_valid_forecast(self) -> None:
        forecast = _forecast()

        validate_forecast_for_storage(forecast)

    def test_rejects_non_datetime_timestamps(self) -> None:
        forecast = _forecast()

        forecast.predictions["timestamp"] = [
            "a",
            "b",
        ]

        with pytest.raises(
            TypeError,
            match=("Forecast prediction timestamps must contain " "datetime values."),
        ):
            validate_forecast_for_storage(forecast)

    def test_rejects_missing_timestamps(self) -> None:
        forecast = _forecast()
        forecast.predictions.loc[0, "timestamp"] = pd.NaT

        with pytest.raises(
            ValueError,
            match=(
                "Forecast prediction timestamps must not contain " "missing values."
            ),
        ):
            validate_forecast_for_storage(forecast)

    def test_rejects_non_numeric_predictions(self) -> None:
        forecast = _forecast()

        forecast.predictions["prediction"] = [
            "low",
            "high",
        ]

        with pytest.raises(
            TypeError,
            match="Forecast prediction values must be numeric.",
        ):
            validate_forecast_for_storage(forecast)

    def test_rejects_missing_predictions(self) -> None:
        forecast = _forecast()
        forecast.predictions.loc[0, "prediction"] = float("nan")

        with pytest.raises(
            ValueError,
            match=("Forecast prediction values must not contain " "missing values."),
        ):
            validate_forecast_for_storage(forecast)
