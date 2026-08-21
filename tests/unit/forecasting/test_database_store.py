"""Unit tests for EOIP database-backed forecast storage."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest
from sqlalchemy import create_engine

from eoip.forecasting.database_store import DatabaseForecastStore
from eoip.forecasting.models.base import ForecastResult


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
                        "2026-08-18T10:30:00Z",
                    ],
                    utc=True,
                ),
                "prediction": [
                    500.0,
                    510.0,
                    520.0,
                ],
            }
        ),
    )


@pytest.fixture
def store() -> DatabaseForecastStore:
    """Return an in-memory database forecast store."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
    )

    forecast_store = DatabaseForecastStore(
        engine=engine,
    )

    forecast_store.create_schema()

    return forecast_store


class TestDatabaseForecastStoreSave:
    """Tests for forecast persistence."""

    def test_save_returns_metadata(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        generated_at = datetime(
            2026,
            8,
            18,
            10,
            0,
            tzinfo=UTC,
        )

        result = store.save(
            forecast=_forecast(),
            generated_at=generated_at,
        )

        assert result.forecast_id
        assert result.model_name == "Naive"
        assert result.target_column == "active_power_kw"
        assert result.generated_at == generated_at
        assert result.row_count == 3

    def test_save_generates_unique_forecast_ids(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        generated_at = datetime(
            2026,
            8,
            18,
            10,
            0,
            tzinfo=UTC,
        )

        first = store.save(
            forecast=_forecast(),
            generated_at=generated_at,
        )

        second = store.save(
            forecast=_forecast(),
            generated_at=generated_at,
        )

        assert first.forecast_id != second.forecast_id

    def test_rejects_naive_generated_at(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="generated_at must be timezone-aware.",
        ):
            store.save(
                forecast=_forecast(),
                generated_at=datetime(
                    2026,
                    8,
                    18,
                    10,
                    0,
                ),
            )


class TestDatabaseForecastStoreLoad:
    """Tests for loading persisted forecasts."""

    def test_load_returns_saved_predictions(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        metadata = store.save(
            forecast=_forecast(),
            generated_at=datetime(
                2026,
                8,
                18,
                10,
                0,
                tzinfo=UTC,
            ),
        )

        result = store.load(
            forecast_id=metadata.forecast_id,
        )

        assert list(result.columns) == [
            "timestamp",
            "prediction",
        ]

        assert len(result) == 3

        assert result["prediction"].tolist() == [
            500.0,
            510.0,
            520.0,
        ]

    def test_load_sorts_predictions_by_timestamp(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        original = _forecast()

        shuffled_predictions = original.predictions.iloc[
            [
                2,
                0,
                1,
            ]
        ].reset_index(drop=True)

        forecast = ForecastResult(
            model_name=original.model_name,
            target_column=original.target_column,
            predictions=shuffled_predictions,
        )

        metadata = store.save(
            forecast=forecast,
            generated_at=datetime(
                2026,
                8,
                18,
                10,
                0,
                tzinfo=UTC,
            ),
        )

        result = store.load(
            forecast_id=metadata.forecast_id,
        )

        assert result["timestamp"].is_monotonic_increasing

        assert result["prediction"].tolist() == [
            500.0,
            510.0,
            520.0,
        ]

    def test_rejects_empty_forecast_id(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="forecast_id must not be empty.",
        ):
            store.load(
                forecast_id=" ",
            )

    def test_raises_for_missing_forecast(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        with pytest.raises(
            KeyError,
            match="Forecast not found: missing-id",
        ):
            store.load(
                forecast_id="missing-id",
            )


class TestDatabaseForecastStoreMetadata:
    """Tests for stored forecast metadata retrieval."""

    def test_get_metadata_returns_saved_metadata(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        generated_at = datetime(
            2026,
            8,
            18,
            10,
            0,
            tzinfo=UTC,
        )

        saved = store.save(
            forecast=_forecast(),
            generated_at=generated_at,
        )

        result = store.get_metadata(
            forecast_id=saved.forecast_id,
        )

        assert result.forecast_id == saved.forecast_id
        assert result.model_name == "Naive"
        assert result.target_column == "active_power_kw"
        assert result.row_count == 3

    def test_rejects_empty_forecast_id(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="forecast_id must not be empty.",
        ):
            store.get_metadata(
                forecast_id=" ",
            )

    def test_raises_for_missing_forecast(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        with pytest.raises(
            KeyError,
            match="Forecast not found: missing-id",
        ):
            store.get_metadata(
                forecast_id="missing-id",
            )


class TestDatabaseForecastStoreDelete:
    """Tests for deleting stored forecasts."""

    def test_delete_removes_forecast(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        saved = store.save(
            forecast=_forecast(),
            generated_at=datetime(
                2026,
                8,
                18,
                10,
                0,
                tzinfo=UTC,
            ),
        )

        store.delete(
            forecast_id=saved.forecast_id,
        )

        with pytest.raises(
            KeyError,
            match=f"Forecast not found: {saved.forecast_id}",
        ):
            store.load(
                forecast_id=saved.forecast_id,
            )

    def test_delete_removes_metadata(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        saved = store.save(
            forecast=_forecast(),
            generated_at=datetime(
                2026,
                8,
                18,
                10,
                0,
                tzinfo=UTC,
            ),
        )

        store.delete(
            forecast_id=saved.forecast_id,
        )

        with pytest.raises(
            KeyError,
            match=f"Forecast not found: {saved.forecast_id}",
        ):
            store.get_metadata(
                forecast_id=saved.forecast_id,
            )

    def test_rejects_empty_forecast_id(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="forecast_id must not be empty.",
        ):
            store.delete(
                forecast_id=" ",
            )

    def test_raises_for_missing_forecast(
        self,
        store: DatabaseForecastStore,
    ) -> None:
        with pytest.raises(
            KeyError,
            match="Forecast not found: missing-id",
        ):
            store.delete(
                forecast_id="missing-id",
            )
