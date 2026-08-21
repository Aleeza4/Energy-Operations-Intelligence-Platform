"""Energy-loss analysis for EOIP optimization."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class EnergyLossResult:
    """Energy-loss result for one operating period."""

    actual_energy_kwh: float
    expected_energy_kwh: float
    energy_loss_kwh: float
    loss_percentage: float

    def __post_init__(self) -> None:
        """Validate energy-loss result."""
        values = {
            "actual_energy_kwh": self.actual_energy_kwh,
            "expected_energy_kwh": self.expected_energy_kwh,
            "energy_loss_kwh": self.energy_loss_kwh,
            "loss_percentage": self.loss_percentage,
        }

        for name, value in values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        if self.actual_energy_kwh < 0.0:
            raise ValueError("actual_energy_kwh must not be negative.")

        if self.expected_energy_kwh < 0.0:
            raise ValueError("expected_energy_kwh must not be negative.")

        if self.energy_loss_kwh < 0.0:
            raise ValueError("energy_loss_kwh must not be negative.")

        if not 0.0 <= self.loss_percentage <= 100.0:
            raise ValueError("loss_percentage must be between 0 and 100.")


def calculate_energy_loss(
    *,
    actual_energy_kwh: float,
    expected_energy_kwh: float,
) -> EnergyLossResult:
    """Calculate energy loss relative to expected production."""
    values = {
        "actual_energy_kwh": actual_energy_kwh,
        "expected_energy_kwh": expected_energy_kwh,
    }

    for name, value in values.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

    if actual_energy_kwh < 0.0:
        raise ValueError("actual_energy_kwh must not be negative.")

    if expected_energy_kwh < 0.0:
        raise ValueError("expected_energy_kwh must not be negative.")

    energy_loss_kwh = max(
        expected_energy_kwh - actual_energy_kwh,
        0.0,
    )

    if expected_energy_kwh == 0.0:
        loss_percentage = 0.0
    else:
        loss_percentage = energy_loss_kwh / expected_energy_kwh * 100.0

    return EnergyLossResult(
        actual_energy_kwh=float(actual_energy_kwh),
        expected_energy_kwh=float(expected_energy_kwh),
        energy_loss_kwh=float(energy_loss_kwh),
        loss_percentage=float(loss_percentage),
    )


def analyze_energy_losses(
    *,
    frame: pd.DataFrame,
    actual_energy_column: str = "actual_energy_kwh",
    expected_energy_column: str = "expected_energy_kwh",
) -> pd.DataFrame:
    """Calculate energy losses for multiple operating periods."""
    if frame.empty:
        raise ValueError("Energy loss frame must not be empty.")

    if not actual_energy_column.strip():
        raise ValueError("actual_energy_column must not be empty.")

    if not expected_energy_column.strip():
        raise ValueError("expected_energy_column must not be empty.")

    required_columns = {
        actual_energy_column,
        expected_energy_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Energy loss frame is missing required columns: " f"{missing_columns}"
        )

    actual = frame[actual_energy_column]

    expected = frame[expected_energy_column]

    if not pd.api.types.is_numeric_dtype(actual):
        raise TypeError("Actual energy column must be numeric.")

    if not pd.api.types.is_numeric_dtype(expected):
        raise TypeError("Expected energy column must be numeric.")

    if actual.isna().any():
        raise ValueError("Actual energy column must not contain missing values.")

    if expected.isna().any():
        raise ValueError("Expected energy column must not contain missing values.")

    actual_values = actual.to_numpy(dtype=float)

    expected_values = expected.to_numpy(dtype=float)

    if not np.isfinite(actual_values).all():
        raise ValueError("Actual energy values must contain only finite values.")

    if not np.isfinite(expected_values).all():
        raise ValueError("Expected energy values must contain only finite values.")

    if (actual_values < 0.0).any():
        raise ValueError("Actual energy values must not be negative.")

    if (expected_values < 0.0).any():
        raise ValueError("Expected energy values must not be negative.")

    result = frame.copy(deep=True)

    energy_loss = np.maximum(
        expected_values - actual_values,
        0.0,
    )

    loss_percentage = np.divide(
        energy_loss * 100.0,
        expected_values,
        out=np.zeros_like(
            energy_loss,
            dtype=float,
        ),
        where=expected_values != 0.0,
    )

    result["energy_loss_kwh"] = energy_loss

    result["loss_percentage"] = loss_percentage

    return result
