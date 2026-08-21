"""Training pipeline utilities for EOIP forecasting models."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from eoip.forecasting.models.base import ForecastModel


@dataclass(frozen=True, slots=True)
class TrainingResult:
    """Summary returned after a forecasting model is trained."""

    model_name: str
    target_column: str
    row_count: int
    timestamp_column: str

    def __post_init__(self) -> None:
        """Validate training result metadata."""
        if not self.model_name.strip():
            raise ValueError("model_name must not be empty.")

        if not self.target_column.strip():
            raise ValueError("target_column must not be empty.")

        if not self.timestamp_column.strip():
            raise ValueError("timestamp_column must not be empty.")

        if self.row_count < 1:
            raise ValueError("row_count must be greater than zero.")


def train_forecast_model(
    *,
    model: ForecastModel,
    frame: pd.DataFrame,
    timestamp_column: str,
    target_column: str,
) -> TrainingResult:
    """Train a forecasting model and return training metadata."""
    if frame.empty:
        raise ValueError("Training frame must not be empty.")

    if timestamp_column not in frame.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_column}")

    if target_column not in frame.columns:
        raise ValueError(f"Missing target column: {target_column}")

    model.fit(
        frame=frame,
        timestamp_column=timestamp_column,
        target_column=target_column,
    )

    return TrainingResult(
        model_name=model.name,
        target_column=target_column,
        row_count=len(frame),
        timestamp_column=timestamp_column,
    )
