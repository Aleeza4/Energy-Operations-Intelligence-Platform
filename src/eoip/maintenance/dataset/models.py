"""Dataset models for EOIP predictive maintenance."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class MaintenanceDataset:
    """Validated dataset used by predictive-maintenance models."""

    observations: pd.DataFrame
    timestamp_column: str
    equipment_id_column: str
    target_column: str

    def __post_init__(self) -> None:
        """Validate predictive-maintenance dataset configuration."""
        if self.observations.empty:
            raise ValueError("Maintenance dataset must not be empty.")

        if not self.timestamp_column.strip():
            raise ValueError("timestamp_column must not be empty.")

        if not self.equipment_id_column.strip():
            raise ValueError("equipment_id_column must not be empty.")

        if not self.target_column.strip():
            raise ValueError("target_column must not be empty.")

        required_columns = {
            self.timestamp_column,
            self.equipment_id_column,
            self.target_column,
        }

        missing_columns = required_columns - set(self.observations.columns)

        if missing_columns:
            raise ValueError(
                "Maintenance dataset is missing required columns: "
                f"{sorted(missing_columns)}"
            )

        timestamps = self.observations[self.timestamp_column]

        if not pd.api.types.is_datetime64_any_dtype(timestamps):
            raise TypeError("Maintenance timestamps must contain datetime values.")

        if timestamps.isna().any():
            raise ValueError("Maintenance timestamps must not contain missing values.")

        equipment_ids = self.observations[self.equipment_id_column]

        if equipment_ids.isna().any():
            raise ValueError("Equipment identifiers must not contain missing values.")

        normalized_equipment_ids = equipment_ids.astype(str).str.strip()

        if normalized_equipment_ids.eq("").any():
            raise ValueError("Equipment identifiers must not be empty.")

        target = self.observations[self.target_column]

        if target.isna().any():
            raise ValueError("Maintenance target must not contain missing values.")

        duplicated = self.observations.duplicated(
            subset=[
                self.equipment_id_column,
                self.timestamp_column,
            ]
        )

        if duplicated.any():
            raise ValueError(
                "Maintenance dataset must not contain duplicate "
                "equipment-timestamp observations."
            )

    @property
    def row_count(self) -> int:
        """Return number of observations."""
        return len(self.observations)

    @property
    def equipment_count(self) -> int:
        """Return number of unique equipment assets."""
        return int(self.observations[self.equipment_id_column].nunique())

    @property
    def feature_columns(self) -> tuple[str, ...]:
        """Return columns available as candidate model features."""
        excluded_columns = {
            self.timestamp_column,
            self.equipment_id_column,
            self.target_column,
        }

        return tuple(
            column
            for column in self.observations.columns
            if column not in excluded_columns
        )
