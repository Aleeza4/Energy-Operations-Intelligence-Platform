"""Unit tests for EOIP anomaly storage contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from eoip.anomaly.storage import (
    StoredAnomalyRun,
    validate_anomaly_frame_for_storage,
)


def _frame() -> pd.DataFrame:
    """Return a valid anomaly result frame."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-18T10:00:00Z",
                periods=4,
                freq="15min",
            ),
            "active_power_kw": [
                100.0,
                500.0,
                105.0,
                20.0,
            ],
            "anomaly_score": [
                0.10,
                -0.55,
                0.08,
                -0.42,
            ],
            "is_anomaly": [
                False,
                True,
                False,
                True,
            ],
        }
    )


def _stored_run() -> StoredAnomalyRun:
    """Return valid stored anomaly metadata."""
    return StoredAnomalyRun(
        anomaly_run_id="run-001",
        detector_name="isolation_forest",
        target_column="active_power_kw",
        generated_at=datetime(
            2026,
            8,
            18,
            12,
            0,
            tzinfo=UTC,
        ),
        row_count=4,
        anomaly_count=2,
    )


class TestStoredAnomalyRun:
    """Tests for stored anomaly run metadata."""

    def test_accepts_valid_metadata(self) -> None:
        result = _stored_run()

        assert result.anomaly_run_id == "run-001"
        assert result.detector_name == "isolation_forest"
        assert result.target_column == "active_power_kw"
        assert result.row_count == 4
        assert result.anomaly_count == 2

    def test_preserves_generated_at(self) -> None:
        result = _stored_run()

        assert result.generated_at == datetime(
            2026,
            8,
            18,
            12,
            0,
            tzinfo=UTC,
        )

    def test_is_frozen(self) -> None:
        result = _stored_run()

        with pytest.raises(
            AttributeError,
        ):
            result.row_count = 10  # type: ignore[misc]

    def test_rejects_empty_anomaly_run_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="anomaly_run_id must not be empty.",
        ):
            StoredAnomalyRun(
                anomaly_run_id=" ",
                detector_name="isolation_forest",
                target_column="active_power_kw",
                generated_at=datetime.now(UTC),
                row_count=4,
                anomaly_count=2,
            )

    def test_rejects_empty_detector_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="detector_name must not be empty.",
        ):
            StoredAnomalyRun(
                anomaly_run_id="run-001",
                detector_name=" ",
                target_column="active_power_kw",
                generated_at=datetime.now(UTC),
                row_count=4,
                anomaly_count=2,
            )

    def test_rejects_empty_target_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            StoredAnomalyRun(
                anomaly_run_id="run-001",
                detector_name="isolation_forest",
                target_column=" ",
                generated_at=datetime.now(UTC),
                row_count=4,
                anomaly_count=2,
            )

    def test_rejects_naive_generated_at(self) -> None:
        with pytest.raises(
            ValueError,
            match="generated_at must be timezone-aware.",
        ):
            StoredAnomalyRun(
                anomaly_run_id="run-001",
                detector_name="isolation_forest",
                target_column="active_power_kw",
                generated_at=datetime(
                    2026,
                    8,
                    18,
                    12,
                    0,
                ),
                row_count=4,
                anomaly_count=2,
            )

    @pytest.mark.parametrize(
        "row_count",
        [
            0,
            -1,
            -10,
        ],
    )
    def test_rejects_non_positive_row_count(
        self,
        row_count: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="row_count must be greater than zero.",
        ):
            StoredAnomalyRun(
                anomaly_run_id="run-001",
                detector_name="isolation_forest",
                target_column="active_power_kw",
                generated_at=datetime.now(UTC),
                row_count=row_count,
                anomaly_count=0,
            )

    def test_rejects_negative_anomaly_count(self) -> None:
        with pytest.raises(
            ValueError,
            match="anomaly_count must not be negative.",
        ):
            StoredAnomalyRun(
                anomaly_run_id="run-001",
                detector_name="isolation_forest",
                target_column="active_power_kw",
                generated_at=datetime.now(UTC),
                row_count=4,
                anomaly_count=-1,
            )

    def test_rejects_anomaly_count_greater_than_row_count(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="anomaly_count must not exceed row_count.",
        ):
            StoredAnomalyRun(
                anomaly_run_id="run-001",
                detector_name="isolation_forest",
                target_column="active_power_kw",
                generated_at=datetime.now(UTC),
                row_count=4,
                anomaly_count=5,
            )

    def test_allows_zero_anomalies(self) -> None:
        result = StoredAnomalyRun(
            anomaly_run_id="run-001",
            detector_name="z_score",
            target_column="active_power_kw",
            generated_at=datetime.now(UTC),
            row_count=4,
            anomaly_count=0,
        )

        assert result.anomaly_count == 0

    def test_allows_all_rows_to_be_anomalies(self) -> None:
        result = StoredAnomalyRun(
            anomaly_run_id="run-001",
            detector_name="z_score",
            target_column="active_power_kw",
            generated_at=datetime.now(UTC),
            row_count=4,
            anomaly_count=4,
        )

        assert result.anomaly_count == 4


class TestValidateAnomalyFrameForStorage:
    """Tests for anomaly frame storage validation."""

    def test_accepts_valid_frame(self) -> None:
        validate_anomaly_frame_for_storage(_frame())

    def test_accepts_additional_columns(self) -> None:
        frame = _frame()

        frame["plant_id"] = "plant-001"
        frame["severity"] = "high"

        validate_anomaly_frame_for_storage(frame)

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Anomaly result frame must not be empty.",
        ):
            validate_anomaly_frame_for_storage(pd.DataFrame())

    def test_rejects_missing_timestamp_column(self) -> None:
        frame = _frame().drop(columns=["timestamp"])

        with pytest.raises(
            ValueError,
            match=("Anomaly result frame is missing required columns"),
        ):
            validate_anomaly_frame_for_storage(frame)

    def test_rejects_missing_anomaly_column(self) -> None:
        frame = _frame().drop(columns=["is_anomaly"])

        with pytest.raises(
            ValueError,
            match=("Anomaly result frame is missing required columns"),
        ):
            validate_anomaly_frame_for_storage(frame)

    def test_rejects_all_missing_required_columns(self) -> None:
        frame = pd.DataFrame(
            {
                "active_power_kw": [
                    100.0,
                    200.0,
                ],
            }
        )

        with pytest.raises(
            ValueError,
            match=("Anomaly result frame is missing required columns"),
        ):
            validate_anomaly_frame_for_storage(frame)

    def test_rejects_non_datetime_timestamp(self) -> None:
        frame = _frame()

        frame["timestamp"] = [
            "2026-08-18T10:00:00Z",
            "2026-08-18T10:15:00Z",
            "2026-08-18T10:30:00Z",
            "2026-08-18T10:45:00Z",
        ]

        with pytest.raises(
            TypeError,
            match=("Anomaly timestamps must contain datetime values."),
        ):
            validate_anomaly_frame_for_storage(frame)

    def test_rejects_missing_timestamp_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "timestamp",
        ] = pd.NaT

        with pytest.raises(
            ValueError,
            match=("Anomaly timestamps must not contain missing values."),
        ):
            validate_anomaly_frame_for_storage(frame)

    def test_rejects_non_boolean_anomaly_flags(self) -> None:
        frame = _frame()

        frame["is_anomaly"] = [
            0,
            1,
            0,
            1,
        ]

        with pytest.raises(
            TypeError,
            match="Anomaly flags must be boolean.",
        ):
            validate_anomaly_frame_for_storage(frame)

    def test_rejects_missing_anomaly_flags(self) -> None:
        frame = _frame()

        frame["is_anomaly"] = frame["is_anomaly"].astype("boolean")

        frame.loc[
            0,
            "is_anomaly",
        ] = pd.NA

        with pytest.raises(
            ValueError,
            match=("Anomaly flags must not contain missing values."),
        ):
            validate_anomaly_frame_for_storage(frame)
