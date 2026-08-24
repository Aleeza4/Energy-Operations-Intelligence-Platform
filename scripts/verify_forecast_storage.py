"""Verify EOIP forecast storage against PostgreSQL."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import create_engine

from eoip.forecasting.database_store import DatabaseForecastStore
from eoip.forecasting.models.base import ForecastResult


def main() -> None:
    """Run forecast storage verification."""
    database_url = os.getenv("EOIP_DATABASE_URL")

    if not database_url:
        raise RuntimeError("EOIP_DATABASE_URL is not configured.")

    engine = create_engine(
        database_url,
        future=True,
    )

    store = DatabaseForecastStore(
        engine=engine,
    )

    forecast = ForecastResult(
        model_name="Storage Verification Model",
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

    generated_at = datetime.now(UTC)

    stored = store.save(
        forecast=forecast,
        generated_at=generated_at,
    )

    print("SAVE OK")
    print(stored)

    metadata = store.get_metadata(
        forecast_id=stored.forecast_id,
    )

    print("METADATA OK")
    print(metadata)

    loaded = store.load(
        forecast_id=stored.forecast_id,
    )

    print("LOAD OK")
    print(loaded)

    assert len(loaded) == 3
    assert loaded["prediction"].tolist() == [
        500.0,
        510.0,
        520.0,
    ]

    store.delete(
        forecast_id=stored.forecast_id,
    )

    print("DELETE OK")

    try:
        store.load(
            forecast_id=stored.forecast_id,
        )
    except KeyError:
        print("DELETE VERIFICATION OK")
    else:
        raise AssertionError("Deleted forecast was still available.")

    engine.dispose()

    print("FORECAST STORAGE VERIFICATION PASSED")


if __name__ == "__main__":
    main()
