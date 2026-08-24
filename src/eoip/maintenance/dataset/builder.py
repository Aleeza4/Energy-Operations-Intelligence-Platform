"""Dataset builder for EOIP predictive maintenance."""

from __future__ import annotations

import pandas as pd

from eoip.maintenance.dataset.models import MaintenanceDataset


def build_maintenance_dataset(
    *,
    frame: pd.DataFrame,
    timestamp_column: str,
    equipment_id_column: str,
    target_column: str,
) -> MaintenanceDataset:
    """Build a validated predictive-maintenance dataset."""
    if frame.empty:
        raise ValueError("Source maintenance frame must not be empty.")

    if not timestamp_column.strip():
        raise ValueError("timestamp_column must not be empty.")

    if not equipment_id_column.strip():
        raise ValueError("equipment_id_column must not be empty.")

    if not target_column.strip():
        raise ValueError("target_column must not be empty.")

    required_columns = {
        timestamp_column,
        equipment_id_column,
        target_column,
    }

    missing_columns = required_columns - set(frame.columns)

    if missing_columns:
        raise ValueError(
            "Source maintenance frame is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    result = frame.copy(deep=True)

    try:
        result[timestamp_column] = pd.to_datetime(
            result[timestamp_column],
            utc=True,
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Maintenance timestamp column contains invalid values."
        ) from exc

    if result[timestamp_column].isna().any():
        raise ValueError("Maintenance timestamp column contains missing values.")

    equipment_ids = result[equipment_id_column]

    if equipment_ids.isna().any():
        raise ValueError("Equipment identifier column contains missing values.")

    result[equipment_id_column] = equipment_ids.astype(str).str.strip()

    if result[equipment_id_column].eq("").any():
        raise ValueError("Equipment identifier column contains empty values.")

    if result[target_column].isna().any():
        raise ValueError("Maintenance target column contains missing values.")

    duplicated = result.duplicated(
        subset=[
            equipment_id_column,
            timestamp_column,
        ]
    )

    if duplicated.any():
        raise ValueError(
            "Source maintenance frame contains duplicate "
            "equipment-timestamp observations."
        )

    result = result.sort_values(
        by=[
            equipment_id_column,
            timestamp_column,
        ],
        kind="stable",
    ).reset_index(drop=True)

    return MaintenanceDataset(
        observations=result,
        timestamp_column=timestamp_column,
        equipment_id_column=equipment_id_column,
        target_column=target_column,
    )
