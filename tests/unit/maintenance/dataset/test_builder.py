"""Unit tests for EOIP predictive-maintenance dataset builder."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.maintenance.dataset.builder import build_maintenance_dataset


def _frame() -> pd.DataFrame:
    """Return a valid unsorted maintenance source frame."""
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-08-18T10:30:00Z",
                "2026-08-18T10:00:00Z",
                "2026-08-18T10:45:00Z",
                "2026-08-18T10:15:00Z",
            ],
            "equipment_id": [
                "INV-002",
                "INV-001",
                "INV-002",
                "INV-001",
            ],
            "failure_within_window": [
                False,
                False,
                False,
                True,
            ],
            "active_power_kw": [
                600.0,
                500.0,
                610.0,
                450.0,
            ],
            "temperature_c": [
                43.0,
                45.0,
                44.0,
                52.0,
            ],
        }
    )


class TestBuildMaintenanceDataset:
    """Tests for maintenance dataset construction."""

    def test_builds_valid_dataset(self) -> None:
        dataset = build_maintenance_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            equipment_id_column="equipment_id",
            target_column="failure_within_window",
        )

        assert dataset.row_count == 4
        assert dataset.equipment_count == 2
        assert dataset.timestamp_column == "timestamp"
        assert dataset.equipment_id_column == "equipment_id"
        assert dataset.target_column == "failure_within_window"

    def test_normalizes_timestamps_to_datetime(self) -> None:
        dataset = build_maintenance_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            equipment_id_column="equipment_id",
            target_column="failure_within_window",
        )

        assert pd.api.types.is_datetime64_any_dtype(dataset.observations["timestamp"])

    def test_normalizes_timestamps_to_utc(self) -> None:
        dataset = build_maintenance_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            equipment_id_column="equipment_id",
            target_column="failure_within_window",
        )

        assert str(dataset.observations["timestamp"].dt.tz) == "UTC"

    def test_strips_equipment_identifiers(self) -> None:
        frame = _frame()

        frame["equipment_id"] = [
            " INV-002 ",
            " INV-001 ",
            "INV-002",
            "INV-001",
        ]

        dataset = build_maintenance_dataset(
            frame=frame,
            timestamp_column="timestamp",
            equipment_id_column="equipment_id",
            target_column="failure_within_window",
        )

        assert dataset.observations["equipment_id"].tolist() == [
            "INV-001",
            "INV-001",
            "INV-002",
            "INV-002",
        ]

    def test_sorts_by_equipment_then_timestamp(self) -> None:
        dataset = build_maintenance_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            equipment_id_column="equipment_id",
            target_column="failure_within_window",
        )

        assert dataset.observations["equipment_id"].tolist() == [
            "INV-001",
            "INV-001",
            "INV-002",
            "INV-002",
        ]

        assert dataset.observations["timestamp"].tolist() == list(
            pd.to_datetime(
                [
                    "2026-08-18T10:00:00Z",
                    "2026-08-18T10:15:00Z",
                    "2026-08-18T10:30:00Z",
                    "2026-08-18T10:45:00Z",
                ],
                utc=True,
            )
        )

    def test_preserves_feature_columns(self) -> None:
        dataset = build_maintenance_dataset(
            frame=_frame(),
            timestamp_column="timestamp",
            equipment_id_column="equipment_id",
            target_column="failure_within_window",
        )

        assert dataset.feature_columns == (
            "active_power_kw",
            "temperature_c",
        )

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        build_maintenance_dataset(
            frame=frame,
            timestamp_column="timestamp",
            equipment_id_column="equipment_id",
            target_column="failure_within_window",
        )

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_source_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Source maintenance frame must not be empty.",
        ):
            build_maintenance_dataset(
                frame=pd.DataFrame(),
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_empty_timestamp_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="timestamp_column must not be empty.",
        ):
            build_maintenance_dataset(
                frame=_frame(),
                timestamp_column=" ",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_empty_equipment_id_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id_column must not be empty.",
        ):
            build_maintenance_dataset(
                frame=_frame(),
                timestamp_column="timestamp",
                equipment_id_column=" ",
                target_column="failure_within_window",
            )

    def test_rejects_empty_target_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            build_maintenance_dataset(
                frame=_frame(),
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column=" ",
            )

    @pytest.mark.parametrize(
        (
            "timestamp_column",
            "equipment_column",
            "target_column",
        ),
        [
            (
                "missing_timestamp",
                "equipment_id",
                "failure_within_window",
            ),
            (
                "timestamp",
                "missing_equipment",
                "failure_within_window",
            ),
            (
                "timestamp",
                "equipment_id",
                "missing_target",
            ),
        ],
    )
    def test_rejects_missing_required_columns(
        self,
        timestamp_column: str,
        equipment_column: str,
        target_column: str,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=("Source maintenance frame is missing required columns"),
        ):
            build_maintenance_dataset(
                frame=_frame(),
                timestamp_column=timestamp_column,
                equipment_id_column=equipment_column,
                target_column=target_column,
            )

    def test_rejects_invalid_timestamp_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "timestamp",
        ] = "not-a-date"

        with pytest.raises(
            ValueError,
            match=("Maintenance timestamp column contains invalid values."),
        ):
            build_maintenance_dataset(
                frame=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_missing_timestamp_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "timestamp",
        ] = None

        with pytest.raises(
            ValueError,
            match=("Maintenance timestamp column contains missing values."),
        ):
            build_maintenance_dataset(
                frame=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_missing_equipment_identifier(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "equipment_id",
        ] = None

        with pytest.raises(
            ValueError,
            match=("Equipment identifier column contains missing values."),
        ):
            build_maintenance_dataset(
                frame=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_blank_equipment_identifier(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "equipment_id",
        ] = "   "

        with pytest.raises(
            ValueError,
            match=("Equipment identifier column contains empty values."),
        ):
            build_maintenance_dataset(
                frame=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )

    def test_rejects_missing_target_value(self) -> None:
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
            match=("Maintenance target column contains missing values."),
        ):
            build_maintenance_dataset(
                frame=frame,
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
            3,
            "timestamp",
        ]

        with pytest.raises(
            ValueError,
            match=(
                "Source maintenance frame contains duplicate "
                "equipment-timestamp observations."
            ),
        ):
            build_maintenance_dataset(
                frame=frame,
                timestamp_column="timestamp",
                equipment_id_column="equipment_id",
                target_column="failure_within_window",
            )
