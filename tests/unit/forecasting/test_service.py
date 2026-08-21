"""Unit tests for EOIP forecast application service."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from eoip.forecasting.models.naive import NaiveForecastModel
from eoip.forecasting.service import ForecastService
from eoip.forecasting.storage import StoredForecast


def _training_frame() -> pd.DataFrame:
    """Return deterministic training data."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-18T08:00:00Z",
                periods=8,
                freq="15min",
            ),
            "active_power_kw": [
                400.0,
                420.0,
                440.0,
                460.0,
                480.0,
                500.0,
                520.0,
                540.0,
            ],
        }
    )


class InMemoryForecastStore:
    """Simple forecast store used by service unit tests."""

    def __init__(self) -> None:
        """Initialize the in-memory store."""
        self._frames: dict[str, pd.DataFrame] = {}
        self._counter = 0

    def save(
        self,
        *,
        forecast,
        generated_at: datetime,
    ) -> StoredForecast:
        """Store forecast predictions in memory."""
        self._counter += 1
        forecast_id = f"forecast-{self._counter}"

        self._frames[forecast_id] = forecast.predictions.copy()

        return StoredForecast(
            forecast_id=forecast_id,
            model_name=forecast.model_name,
            target_column=forecast.target_column,
            generated_at=generated_at,
            row_count=len(forecast.predictions),
        )

    def load(
        self,
        *,
        forecast_id: str,
    ) -> pd.DataFrame:
        """Load stored forecast predictions."""
        if forecast_id not in self._frames:
            raise KeyError(f"Forecast not found: {forecast_id}")

        return self._frames[forecast_id].copy()


class TestForecastServiceGenerate:
    """Tests for forecast generation."""

    def test_generates_forecast(self) -> None:
        service = ForecastService()

        result = service.generate_forecast(
            model=NaiveForecastModel(),
            training_frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
            horizon=3,
            frequency="15min",
        )

        assert result.model_name
        assert result.target_column == "active_power_kw"
        assert len(result.predictions) == 3

        assert list(result.predictions.columns) == [
            "timestamp",
            "prediction",
        ]

    def test_naive_forecast_uses_last_value(
        self,
    ) -> None:
        service = ForecastService()

        result = service.generate_forecast(
            model=NaiveForecastModel(),
            training_frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
            horizon=3,
            frequency="15min",
        )

        assert result.predictions["prediction"].tolist() == [
            540.0,
            540.0,
            540.0,
        ]

    def test_rejects_empty_training_frame(
        self,
    ) -> None:
        service = ForecastService()

        with pytest.raises(
            ValueError,
            match="Training frame must not be empty.",
        ):
            service.generate_forecast(
                model=NaiveForecastModel(),
                training_frame=pd.DataFrame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                horizon=3,
                frequency="15min",
            )

    def test_rejects_missing_timestamp_column(
        self,
    ) -> None:
        service = ForecastService()

        frame = _training_frame().drop(columns=["timestamp"])

        with pytest.raises(
            ValueError,
            match="Missing timestamp column: timestamp",
        ):
            service.generate_forecast(
                model=NaiveForecastModel(),
                training_frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                horizon=3,
                frequency="15min",
            )

    def test_rejects_missing_target_column(
        self,
    ) -> None:
        service = ForecastService()

        frame = _training_frame().drop(columns=["active_power_kw"])

        with pytest.raises(
            ValueError,
            match=("Missing target column: active_power_kw"),
        ):
            service.generate_forecast(
                model=NaiveForecastModel(),
                training_frame=frame,
                timestamp_column="timestamp",
                target_column="active_power_kw",
                horizon=3,
                frequency="15min",
            )

    @pytest.mark.parametrize(
        "horizon",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_horizon(
        self,
        horizon: int,
    ) -> None:
        service = ForecastService()

        with pytest.raises(
            ValueError,
            match="horizon must be greater than zero.",
        ):
            service.generate_forecast(
                model=NaiveForecastModel(),
                training_frame=_training_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                horizon=horizon,
                frequency="15min",
            )

    @pytest.mark.parametrize(
        "frequency",
        [
            "",
            " ",
            "   ",
        ],
    )
    def test_rejects_empty_frequency(
        self,
        frequency: str,
    ) -> None:
        service = ForecastService()

        with pytest.raises(
            ValueError,
            match="frequency must not be empty.",
        ):
            service.generate_forecast(
                model=NaiveForecastModel(),
                training_frame=_training_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                horizon=3,
                frequency=frequency,
            )


class TestForecastServicePersistence:
    """Tests for forecast generation and persistence."""

    def test_generates_and_stores_forecast(
        self,
    ) -> None:
        store = InMemoryForecastStore()

        service = ForecastService(
            store=store,
        )

        generated_at = datetime(
            2026,
            8,
            18,
            12,
            0,
            tzinfo=UTC,
        )

        result = service.generate_and_store_forecast(
            model=NaiveForecastModel(),
            training_frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
            horizon=3,
            frequency="15min",
            generated_at=generated_at,
        )

        assert result.forecast_id == "forecast-1"
        assert result.target_column == "active_power_kw"
        assert result.generated_at == generated_at
        assert result.row_count == 3

    def test_generate_and_store_requires_store(
        self,
    ) -> None:
        service = ForecastService()

        with pytest.raises(
            RuntimeError,
            match="Forecast store is not configured.",
        ):
            service.generate_and_store_forecast(
                model=NaiveForecastModel(),
                training_frame=_training_frame(),
                timestamp_column="timestamp",
                target_column="active_power_kw",
                horizon=3,
                frequency="15min",
                generated_at=datetime(
                    2026,
                    8,
                    18,
                    12,
                    0,
                    tzinfo=UTC,
                ),
            )

    def test_loads_stored_forecast(self) -> None:
        store = InMemoryForecastStore()

        service = ForecastService(
            store=store,
        )

        stored = service.generate_and_store_forecast(
            model=NaiveForecastModel(),
            training_frame=_training_frame(),
            timestamp_column="timestamp",
            target_column="active_power_kw",
            horizon=3,
            frequency="15min",
            generated_at=datetime(
                2026,
                8,
                18,
                12,
                0,
                tzinfo=UTC,
            ),
        )

        result = service.load_forecast(
            forecast_id=stored.forecast_id,
        )

        assert len(result) == 3

        assert result["prediction"].tolist() == [
            540.0,
            540.0,
            540.0,
        ]

    def test_load_requires_store(self) -> None:
        service = ForecastService()

        with pytest.raises(
            RuntimeError,
            match="Forecast store is not configured.",
        ):
            service.load_forecast(
                forecast_id="forecast-1",
            )

    def test_load_rejects_empty_forecast_id(
        self,
    ) -> None:
        service = ForecastService(
            store=InMemoryForecastStore(),
        )

        with pytest.raises(
            ValueError,
            match="forecast_id must not be empty.",
        ):
            service.load_forecast(
                forecast_id=" ",
            )

    def test_load_propagates_missing_forecast(
        self,
    ) -> None:
        service = ForecastService(
            store=InMemoryForecastStore(),
        )

        with pytest.raises(
            KeyError,
            match="Forecast not found: missing-id",
        ):
            service.load_forecast(
                forecast_id="missing-id",
            )
