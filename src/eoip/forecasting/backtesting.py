"""Backtesting utilities for EOIP forecasting models."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from eoip.forecasting.models.base import ForecastModel, ForecastResult


@dataclass(frozen=True, slots=True)
class BacktestFoldResult:
    """Result for one forecasting backtest fold."""

    fold: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    forecast: ForecastResult
    actuals: pd.DataFrame

    def __post_init__(self) -> None:
        """Validate fold result."""
        if self.fold < 1:
            raise ValueError("fold must be greater than zero.")

        if self.actuals.empty:
            raise ValueError("Backtest actuals must not be empty.")

        required_columns = {
            "timestamp",
            "actual",
        }

        missing_columns = required_columns - set(self.actuals.columns)

        if missing_columns:
            raise ValueError(
                "Backtest actuals are missing required columns: "
                f"{sorted(missing_columns)}"
            )


def expanding_window_backtest(
    *,
    model_factory: Callable[[], ForecastModel],
    frame: pd.DataFrame,
    timestamp_column: str,
    target_column: str,
    initial_train_size: int,
    horizon: int,
    step_size: int,
    frequency: str,
) -> list[BacktestFoldResult]:
    """Run expanding-window backtesting.

    Each fold trains on all observations available up to that point and
    forecasts the next ``horizon`` observations.
    """
    if frame.empty:
        raise ValueError("Backtest frame must not be empty.")

    if timestamp_column not in frame.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_column}")

    if target_column not in frame.columns:
        raise ValueError(f"Missing target column: {target_column}")

    if initial_train_size < 1:
        raise ValueError("initial_train_size must be greater than zero.")

    if horizon < 1:
        raise ValueError("horizon must be greater than zero.")

    if step_size < 1:
        raise ValueError("step_size must be greater than zero.")

    if not frequency.strip():
        raise ValueError("frequency must not be empty.")

    ordered = frame.copy()

    ordered[timestamp_column] = pd.to_datetime(
        ordered[timestamp_column],
        utc=True,
        errors="raise",
    )

    ordered = ordered.sort_values(timestamp_column).reset_index(drop=True)

    if len(ordered) < initial_train_size + horizon:
        raise ValueError(
            "Backtest frame does not contain enough observations "
            "for the requested initial training size and horizon."
        )

    results: list[BacktestFoldResult] = []

    fold = 1
    train_end_index = initial_train_size

    while train_end_index + horizon <= len(ordered):
        train_frame = ordered.iloc[:train_end_index].copy()

        test_frame = ordered.iloc[train_end_index : train_end_index + horizon].copy()

        model = model_factory()

        model.fit(
            frame=train_frame,
            timestamp_column=timestamp_column,
            target_column=target_column,
        )

        forecast = model.predict(
            horizon=horizon,
            frequency=frequency,
        )

        actuals = pd.DataFrame(
            {
                "timestamp": test_frame[timestamp_column].to_numpy(),
                "actual": test_frame[target_column].astype(float).to_numpy(),
            }
        )

        results.append(
            BacktestFoldResult(
                fold=fold,
                train_start=train_frame[timestamp_column].iloc[0],
                train_end=train_frame[timestamp_column].iloc[-1],
                test_start=test_frame[timestamp_column].iloc[0],
                test_end=test_frame[timestamp_column].iloc[-1],
                forecast=forecast,
                actuals=actuals,
            )
        )

        fold += 1
        train_end_index += step_size

    return results
