"""Recoverable-opportunity analysis for EOIP optimization."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class RecoverableOpportunityResult:
    """Recoverable energy opportunity for one operating period."""

    energy_loss_kwh: float
    recoverability_factor: float
    recoverable_energy_kwh: float
    unrecoverable_energy_kwh: float

    def __post_init__(self) -> None:
        """Validate recoverable-opportunity result."""
        values = {
            "energy_loss_kwh": self.energy_loss_kwh,
            "recoverability_factor": self.recoverability_factor,
            "recoverable_energy_kwh": self.recoverable_energy_kwh,
            "unrecoverable_energy_kwh": self.unrecoverable_energy_kwh,
        }

        for name, value in values.items():
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        if self.energy_loss_kwh < 0.0:
            raise ValueError("energy_loss_kwh must not be negative.")

        if not 0.0 <= self.recoverability_factor <= 1.0:
            raise ValueError("recoverability_factor must be between 0 and 1.")

        if self.recoverable_energy_kwh < 0.0:
            raise ValueError("recoverable_energy_kwh must not be negative.")

        if self.unrecoverable_energy_kwh < 0.0:
            raise ValueError("unrecoverable_energy_kwh must not be negative.")

        if not np.isclose(
            self.recoverable_energy_kwh + self.unrecoverable_energy_kwh,
            self.energy_loss_kwh,
        ):
            raise ValueError(
                "Recoverable and unrecoverable energy must sum " "to total energy loss."
            )


def calculate_recoverable_opportunity(
    *,
    energy_loss_kwh: float,
    recoverability_factor: float,
) -> RecoverableOpportunityResult:
    """Calculate technically recoverable energy opportunity."""
    values = {
        "energy_loss_kwh": energy_loss_kwh,
        "recoverability_factor": recoverability_factor,
    }

    for name, value in values.items():
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite.")

    if energy_loss_kwh < 0.0:
        raise ValueError("energy_loss_kwh must not be negative.")

    if not 0.0 <= recoverability_factor <= 1.0:
        raise ValueError("recoverability_factor must be between 0 and 1.")

    recoverable_energy_kwh = energy_loss_kwh * recoverability_factor

    unrecoverable_energy_kwh = energy_loss_kwh - recoverable_energy_kwh

    return RecoverableOpportunityResult(
        energy_loss_kwh=float(energy_loss_kwh),
        recoverability_factor=float(recoverability_factor),
        recoverable_energy_kwh=float(recoverable_energy_kwh),
        unrecoverable_energy_kwh=float(unrecoverable_energy_kwh),
    )


def analyze_recoverable_opportunities(
    *,
    frame: pd.DataFrame,
    energy_loss_column: str = "energy_loss_kwh",
    recoverability_factor_column: str = "recoverability_factor",
) -> pd.DataFrame:
    """Calculate recoverable energy opportunities for multiple rows."""
    if frame.empty:
        raise ValueError("Recoverable opportunity frame must not be empty.")

    if not energy_loss_column.strip():
        raise ValueError("energy_loss_column must not be empty.")

    if not recoverability_factor_column.strip():
        raise ValueError("recoverability_factor_column must not be empty.")

    required_columns = {
        energy_loss_column,
        recoverability_factor_column,
    }

    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        raise ValueError(
            "Recoverable opportunity frame is missing required columns: "
            f"{missing_columns}"
        )

    energy_loss = frame[energy_loss_column]

    recoverability = frame[recoverability_factor_column]

    if not pd.api.types.is_numeric_dtype(energy_loss):
        raise TypeError("Energy loss column must be numeric.")

    if not pd.api.types.is_numeric_dtype(recoverability):
        raise TypeError("Recoverability factor column must be numeric.")

    if energy_loss.isna().any():
        raise ValueError("Energy loss column must not contain missing values.")

    if recoverability.isna().any():
        raise ValueError(
            "Recoverability factor column must not contain missing values."
        )

    energy_loss_values = energy_loss.to_numpy(dtype=float)

    recoverability_values = recoverability.to_numpy(dtype=float)

    if not np.isfinite(energy_loss_values).all():
        raise ValueError("Energy loss values must contain only finite values.")

    if not np.isfinite(recoverability_values).all():
        raise ValueError("Recoverability factors must contain only finite values.")

    if (energy_loss_values < 0.0).any():
        raise ValueError("Energy loss values must not be negative.")

    if ((recoverability_values < 0.0) | (recoverability_values > 1.0)).any():
        raise ValueError("Recoverability factors must be between 0 and 1.")

    result = frame.copy(deep=True)

    recoverable = energy_loss_values * recoverability_values

    unrecoverable = energy_loss_values - recoverable

    result["recoverable_energy_kwh"] = recoverable

    result["unrecoverable_energy_kwh"] = unrecoverable

    return result
