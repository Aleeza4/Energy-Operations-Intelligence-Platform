"""Unit tests for EOIP predictive-maintenance failure windows."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import pytest

from eoip.maintenance.failure_windows import label_failure_windows


def _observations() -> pd.DataFrame:
    """Return deterministic maintenance observations."""
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-08-18T08:00:00Z",
                "2026-08-18T12:00:00Z",
                "2026-08-18T18:00:00Z",
                "2026-08-18T08:00:00Z",
                "2026-08-18T12:00:00Z",
            ],
            "equipment_id": [
                "INV-001",
                "INV-001",
                "INV-001",
                "INV-002",
                "INV-002",
            ],
            "active_power_kw": [
                500.0,
                450.0,
                300.0,
                600.0,
                610.0,
            ],
        }
    )


def _failures() -> pd.DataFrame:
    """Return deterministic equipment failures."""
    return pd.DataFrame(
        {
            "equipment_id": [
                "INV-001",
                "INV-002",
            ],
            "failure_timestamp": [
                "2026-08-19T06:00:00Z",
                "2026-08-20T12:00:00Z",
            ],
        }
    )


class TestLabelFailureWindows:
    """Tests for predictive-maintenance failure labels."""

    def test_labels_failures_within_default_window(self) -> None:
        result = label_failure_windows(
            _observations(),
            _failures(),
        )

        assert result["failure_within_window"].tolist() == [
            True,
            True,
            True,
            False,
            False,
        ]

    def test_supports_custom_prediction_window(self) -> None:
        result = label_failure_windows(
            _observations(),
            _failures(),
            prediction_window=timedelta(hours=12),
        )

        assert result["failure_within_window"].tolist() == [
            False,
            False,
            True,
            False,
            False,
        ]

    def test_supports_custom_target_column(self) -> None:
        result = label_failure_windows(
            _observations(),
            _failures(),
            target_column="failure_next_day",
        )

        assert "failure_next_day" in result.columns

    def test_failure_at_exact_observation_time_is_not_future(
        self,
    ) -> None:
        observations = pd.DataFrame(
            {
                "timestamp": [
                    "2026-08-18T12:00:00Z",
                ],
                "equipment_id": [
                    "INV-001",
                ],
            }
        )

        failures = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-001",
                ],
                "failure_timestamp": [
                    "2026-08-18T12:00:00Z",
                ],
            }
        )

        result = label_failure_windows(
            observations,
            failures,
        )

        assert result["failure_within_window"].tolist() == [
            False,
        ]

    def test_failure_at_exact_window_end_is_included(self) -> None:
        observations = pd.DataFrame(
            {
                "timestamp": [
                    "2026-08-18T12:00:00Z",
                ],
                "equipment_id": [
                    "INV-001",
                ],
            }
        )

        failures = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-001",
                ],
                "failure_timestamp": [
                    "2026-08-19T12:00:00Z",
                ],
            }
        )

        result = label_failure_windows(
            observations,
            failures,
            prediction_window=timedelta(hours=24),
        )

        assert result["failure_within_window"].tolist() == [
            True,
        ]

    def test_failure_after_window_end_is_excluded(self) -> None:
        observations = pd.DataFrame(
            {
                "timestamp": [
                    "2026-08-18T12:00:00Z",
                ],
                "equipment_id": [
                    "INV-001",
                ],
            }
        )

        failures = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-001",
                ],
                "failure_timestamp": [
                    "2026-08-19T12:00:01Z",
                ],
            }
        )

        result = label_failure_windows(
            observations,
            failures,
            prediction_window=timedelta(hours=24),
        )

        assert result["failure_within_window"].tolist() == [
            False,
        ]

    def test_does_not_cross_equipment_boundaries(self) -> None:
        observations = pd.DataFrame(
            {
                "timestamp": [
                    "2026-08-18T12:00:00Z",
                    "2026-08-18T12:00:00Z",
                ],
                "equipment_id": [
                    "INV-001",
                    "INV-002",
                ],
            }
        )

        failures = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-001",
                ],
                "failure_timestamp": [
                    "2026-08-18T18:00:00Z",
                ],
            }
        )

        result = label_failure_windows(
            observations,
            failures,
        )

        assert result["failure_within_window"].tolist() == [
            True,
            False,
        ]

    def test_supports_multiple_failures_per_equipment(self) -> None:
        observations = pd.DataFrame(
            {
                "timestamp": [
                    "2026-08-18T08:00:00Z",
                    "2026-08-20T08:00:00Z",
                ],
                "equipment_id": [
                    "INV-001",
                    "INV-001",
                ],
            }
        )

        failures = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-001",
                    "INV-001",
                ],
                "failure_timestamp": [
                    "2026-08-19T06:00:00Z",
                    "2026-08-21T06:00:00Z",
                ],
            }
        )

        result = label_failure_windows(
            observations,
            failures,
        )

        assert result["failure_within_window"].tolist() == [
            True,
            True,
        ]

    def test_equipment_without_failure_is_false(self) -> None:
        observations = pd.DataFrame(
            {
                "timestamp": [
                    "2026-08-18T12:00:00Z",
                ],
                "equipment_id": [
                    "INV-999",
                ],
            }
        )

        result = label_failure_windows(
            observations,
            _failures(),
        )

        assert result["failure_within_window"].tolist() == [
            False,
        ]

    def test_normalizes_timestamps_to_utc(self) -> None:
        result = label_failure_windows(
            _observations(),
            _failures(),
        )

        assert str(result["timestamp"].dt.tz) == "UTC"

    def test_does_not_mutate_observations(self) -> None:
        observations = _observations()
        original = observations.copy(deep=True)

        label_failure_windows(
            observations,
            _failures(),
        )

        pd.testing.assert_frame_equal(
            observations,
            original,
        )

    def test_does_not_mutate_failures(self) -> None:
        failures = _failures()
        original = failures.copy(deep=True)

        label_failure_windows(
            _observations(),
            failures,
        )

        pd.testing.assert_frame_equal(
            failures,
            original,
        )

    def test_rejects_empty_observations(self) -> None:
        with pytest.raises(
            ValueError,
            match="Observations must not be empty.",
        ):
            label_failure_windows(
                pd.DataFrame(),
                _failures(),
            )

    def test_rejects_empty_failures(self) -> None:
        with pytest.raises(
            ValueError,
            match="Failures must not be empty.",
        ):
            label_failure_windows(
                _observations(),
                pd.DataFrame(),
            )

    @pytest.mark.parametrize(
        "prediction_window",
        [
            timedelta(0),
            timedelta(hours=-1),
        ],
    )
    def test_rejects_non_positive_prediction_window(
        self,
        prediction_window: timedelta,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="prediction_window must be greater than zero.",
        ):
            label_failure_windows(
                _observations(),
                _failures(),
                prediction_window=prediction_window,
            )

    def test_rejects_missing_observation_column(self) -> None:
        frame = _observations().drop(columns=["equipment_id"])

        with pytest.raises(
            ValueError,
            match="Observations are missing required columns",
        ):
            label_failure_windows(
                frame,
                _failures(),
            )

    def test_rejects_missing_failure_column(self) -> None:
        frame = _failures().drop(columns=["failure_timestamp"])

        with pytest.raises(
            ValueError,
            match="Failures are missing required columns",
        ):
            label_failure_windows(
                _observations(),
                frame,
            )

    def test_rejects_invalid_observation_timestamp(self) -> None:
        frame = _observations()

        frame.loc[
            0,
            "timestamp",
        ] = "invalid"

        with pytest.raises(
            ValueError,
            match="Observation timestamps contain invalid values.",
        ):
            label_failure_windows(
                frame,
                _failures(),
            )

    def test_rejects_invalid_failure_timestamp(self) -> None:
        frame = _failures()

        frame.loc[
            0,
            "failure_timestamp",
        ] = "invalid"

        with pytest.raises(
            ValueError,
            match="Failure timestamps contain invalid values.",
        ):
            label_failure_windows(
                _observations(),
                frame,
            )

    def test_rejects_missing_observation_equipment_id(self) -> None:
        frame = _observations()

        frame.loc[
            0,
            "equipment_id",
        ] = None

        with pytest.raises(
            ValueError,
            match=(
                "Observation equipment identifiers must not " "contain missing values."
            ),
        ):
            label_failure_windows(
                frame,
                _failures(),
            )

    def test_rejects_missing_failure_equipment_id(self) -> None:
        frame = _failures()

        frame.loc[
            0,
            "equipment_id",
        ] = None

        with pytest.raises(
            ValueError,
            match=("Failure equipment identifiers must not " "contain missing values."),
        ):
            label_failure_windows(
                _observations(),
                frame,
            )
