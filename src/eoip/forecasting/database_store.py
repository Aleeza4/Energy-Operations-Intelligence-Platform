"""Database-backed forecast storage for EOIP."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    delete,
    insert,
    select,
)
from sqlalchemy.engine import Engine

from eoip.forecasting.models.base import ForecastResult
from eoip.forecasting.storage import (
    StoredForecast,
    validate_forecast_for_storage,
)

_METADATA = MetaData()


forecast_runs = Table(
    "forecast_runs",
    _METADATA,
    Column(
        "forecast_id",
        String(36),
        primary_key=True,
    ),
    Column(
        "model_name",
        String(255),
        nullable=False,
    ),
    Column(
        "target_column",
        String(255),
        nullable=False,
    ),
    Column(
        "generated_at",
        DateTime(timezone=True),
        nullable=False,
    ),
    Column(
        "row_count",
        Integer,
        nullable=False,
    ),
)


forecast_values = Table(
    "forecast_values",
    _METADATA,
    Column(
        "forecast_id",
        String(36),
        nullable=False,
        index=True,
    ),
    Column(
        "timestamp",
        DateTime(timezone=True),
        nullable=False,
    ),
    Column(
        "prediction",
        Float,
        nullable=False,
    ),
)


class DatabaseForecastStore:
    """Persist forecast results using SQLAlchemy."""

    def __init__(
        self,
        *,
        engine: Engine,
    ) -> None:
        """Initialize the forecast database store."""
        self._engine = engine

    def create_schema(self) -> None:
        """Create forecast storage tables when absent."""
        _METADATA.create_all(
            self._engine,
            tables=[
                forecast_runs,
                forecast_values,
            ],
        )

    def save(
        self,
        *,
        forecast: ForecastResult,
        generated_at: datetime,
    ) -> StoredForecast:
        """Persist a forecast and return storage metadata."""
        validate_forecast_for_storage(forecast)

        if generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")

        forecast_id = str(uuid4())

        metadata = StoredForecast(
            forecast_id=forecast_id,
            model_name=forecast.model_name,
            target_column=forecast.target_column,
            generated_at=generated_at,
            row_count=len(forecast.predictions),
        )

        value_records = [
            {
                "forecast_id": forecast_id,
                "timestamp": timestamp.to_pydatetime(),
                "prediction": float(prediction),
            }
            for timestamp, prediction in zip(
                forecast.predictions["timestamp"],
                forecast.predictions["prediction"],
                strict=True,
            )
        ]

        with self._engine.begin() as connection:
            connection.execute(
                insert(forecast_runs),
                {
                    "forecast_id": metadata.forecast_id,
                    "model_name": metadata.model_name,
                    "target_column": metadata.target_column,
                    "generated_at": metadata.generated_at,
                    "row_count": metadata.row_count,
                },
            )

            connection.execute(
                insert(forecast_values),
                value_records,
            )

        return metadata

    def load(
        self,
        *,
        forecast_id: str,
    ) -> pd.DataFrame:
        """Load predictions belonging to a stored forecast."""
        if not forecast_id.strip():
            raise ValueError("forecast_id must not be empty.")

        statement = (
            select(
                forecast_values.c.timestamp,
                forecast_values.c.prediction,
            )
            .where(forecast_values.c.forecast_id == forecast_id)
            .order_by(forecast_values.c.timestamp)
        )

        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()

        if not rows:
            raise KeyError(f"Forecast not found: {forecast_id}")

        frame = pd.DataFrame(rows)

        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"],
            utc=True,
        )

        frame["prediction"] = frame["prediction"].astype(float)

        return frame[
            [
                "timestamp",
                "prediction",
            ]
        ]

    def get_metadata(
        self,
        *,
        forecast_id: str,
    ) -> StoredForecast:
        """Load metadata for a stored forecast."""
        if not forecast_id.strip():
            raise ValueError("forecast_id must not be empty.")

        statement = select(forecast_runs).where(
            forecast_runs.c.forecast_id == forecast_id
        )

        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()

        if row is None:
            raise KeyError(f"Forecast not found: {forecast_id}")

        generated_at = row["generated_at"]

        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=UTC)

        return StoredForecast(
            forecast_id=row["forecast_id"],
            model_name=row["model_name"],
            target_column=row["target_column"],
            generated_at=generated_at,
            row_count=row["row_count"],
        )

    def delete(
        self,
        *,
        forecast_id: str,
    ) -> None:
        """Delete a stored forecast and its predictions."""
        if not forecast_id.strip():
            raise ValueError("forecast_id must not be empty.")

        with self._engine.begin() as connection:
            existing = connection.execute(
                select(forecast_runs.c.forecast_id).where(
                    forecast_runs.c.forecast_id == forecast_id
                )
            ).scalar_one_or_none()

            if existing is None:
                raise KeyError(f"Forecast not found: {forecast_id}")

            connection.execute(
                delete(forecast_values).where(
                    forecast_values.c.forecast_id == forecast_id
                )
            )

            connection.execute(
                delete(forecast_runs).where(forecast_runs.c.forecast_id == forecast_id)
            )
