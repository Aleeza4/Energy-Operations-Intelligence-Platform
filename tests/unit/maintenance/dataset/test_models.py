"""Unit tests for EOIP predictive-maintenance dataset models."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.maintenance.dataset.models import MaintenanceDataset


def _frame() -> pd.DataFrame:
    """Return a valid predictive-maintenance dataset."""
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-08-18T10:00:00Z",
                    "2026-08-18T10:15:00Z",
                    "2026-08-18T10:30:00Z",
                    "2026-08-18T10:45:00Z",
                ],
                utc=True,
            ),
            "equipment_id": [
                "INV-001",
                "INV-001",
                "INV-002",
                "INV-002",
            ],
            "failure_within_window": [
                False,
                True,
                False,
                False,
            ],
            "active_power_kw": [
                500.0,
                450.0,
                600.0,
                610.0,
            ],
            "temperature_c": [
                45.0,
                52.0,
                43.0,
                44.0,
            ],
        }
    )


def _dataset() -> MaintenanceDataset:
    """Return a valid maintenance dataset."""
    return MaintenanceDataset(
        observations=_frame(),
        timestamp_column="timestamp",
        equipment_id_column="equipment_id",
        target_column="failure_within_window",
    )


class TestMaintenanceDatasetValidation:
    """Tests for predictive-maintenance dataset validation."""

    def test_accepts_valid_dataset(self) -> None:
        dataset = _dataset()

        assert dataset.row_count == 4
        assert dataset.equipment_count == 2
        assert dataset.timestamp_column == "timestamp"
        assert dataset.equipment_id_column == "equipment_id"
        assert dataset.target_column == "failure_within_window"

    def test_rejects_empty_dataset(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance dataset must not be empty.",
        ):
            MaintenanceDataset(
                observations=pd.DataFrame(),
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_empty_timestamp_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="timestamp_column must not be empty.",
        ):
            MaintenanceDataset(
                observations=_frame(),
                timestamp_column=" ",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_empty_equipment_id_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id_column must not be empty.",
        ):
            MaintenanceDataset(
                observations=_frame(),
                timestamp_column="timestamp",
                equipment_id_column=" ",
                target_column="failure_within_window",
            )

    def test_rejects_empty_target_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            MaintenanceDataset(
                observations=_frame(),
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column=" ",
            )

    def test_rejects_missing_timestamp_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance dataset is missing required columns",
        ):
            MaintenanceDataset(
                observations=_frame(),
                timestamp_column="missing_timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_missing_equipment_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance dataset is missing required columns",
        ):
            MaintenanceDataset(
                observations=_frame(),
                timestamp_column="timestamp",
                equipment_id_column="missing_equipment",
                target_column="failure_within_window",
            )

    def test_rejects_missing_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance dataset is missing required columns",
        ):
            MaintenanceDataset(
                observations=_frame(),
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="missing_target",
            )

    def test_rejects_non_datetime_timestamps(self) -> None:
        frame = _frame()
        frame["timestamp"] = frame["timestamp"].astype(str)

        with pytest.raises(
            TypeError,
            match="Maintenance timestamps must contain datetime values.",
        ):
            MaintenanceDataset(
                observations=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_missing_timestamp_values(self) -> None:
        frame = _frame()
        frame.loc[0, "timestamp"] = pd.NaT

        with pytest.raises(
            ValueError,
            match="Maintenance timestamps must not contain missing values.",
        ):
            MaintenanceDataset(
                observations=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_missing_equipment_identifier(self) -> None:
        frame = _frame()
        frame.loc[0, "equipment_id"] = None

        with pytest.raises(
            ValueError,
            match="Equipment identifiers must not contain missing values.",
        ):
            MaintenanceDataset(
                observations=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_blank_equipment_identifier(self) -> None:
        frame = _frame()
        frame.loc[0, "equipment_id"] = " "

        with pytest.raises(
            ValueError,
            match="Equipment identifiers must not be empty.",
        ):
            MaintenanceDataset(
                observations=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_missing_target_values(self) -> None:
        frame = _frame()

        frame["failure_within_window"] = frame["failure_within_window"].astype(
            "boolean"
        )

        frame.loc[
            0,
            "failure_within_window",
        ] = pd.NA

        with pytest.raises(
            ValueError,
            match="Maintenance target must not contain missing values.",
        ):
            MaintenanceDataset(
                observations=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_duplicate_equipment_timestamp_pair(self) -> None:
        frame = _frame()

        frame.loc[
            1,
            "timestamp",
        ] = frame.loc[
            0,
            "timestamp",
        ]

        with pytest.raises(
            ValueError,
            match=(
                "Maintenance dataset must not contain duplicate "
                "equipment-timestamp observations."
            ),
        ):
            MaintenanceDataset(
                observations=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )


class TestMaintenanceDatasetProperties:
    """Tests for predictive-maintenance dataset properties."""

    def test_row_count(self) -> None:
        dataset = _dataset()

        assert dataset.row_count == 4

    def test_equipment_count(self) -> None:
        dataset = _dataset()

        assert dataset.equipment_count == 2

    def test_feature_columns(self) -> None:
        dataset = _dataset()

        assert dataset.feature_columns == (
            "active_power_kw",
            "temperature_c",
        )

    def test_feature_columns_exclude_timestamp(self) -> None:
        dataset = _dataset()

        assert "timestamp" not in dataset.feature_columns

    def test_feature_columns_exclude_equipment_identifier(self) -> None:
        dataset = _dataset()

        assert "equipment_id" not in dataset.feature_columns

    def test_feature_columns_exclude_target(self) -> None:
        dataset = _dataset()

        assert "failure_within_window" not in dataset.feature_columns

    def test_feature_columns_preserve_source_order(self) -> None:
        dataset = _dataset()

        assert dataset.feature_columns == (
            "active_power_kw",
            "temperature_c",
        )


class TestMaintenanceDatasetImmutability:
    """Tests for dataclass immutability."""

    def test_dataset_is_frozen(self) -> None:
        dataset = _dataset()

        with pytest.raises(
            AttributeError,
        ):
            dataset.target_column = "other_target"  # type: ignore[misc]
