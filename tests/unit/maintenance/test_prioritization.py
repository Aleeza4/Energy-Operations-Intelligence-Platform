"""Unit tests for EOIP predictive-maintenance prioritization."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.maintenance.prioritization import (
    MaintenancePriorityResult,
    MaintenancePriorityWeights,
    calculate_priority_score,
    prioritize_maintenance,
)


def _frame() -> pd.DataFrame:
    """Return deterministic maintenance-priority inputs."""
    return pd.DataFrame(
        {
            "equipment_id": [
                "INV-001",
                "INV-002",
                "INV-003",
                "INV-004",
            ],
            "risk_score": [
                0.10,
                0.40,
                0.70,
                0.95,
            ],
            "failure_probability": [
                0.05,
                0.30,
                0.65,
                0.90,
            ],
            "health_score": [
                95.0,
                75.0,
                45.0,
                15.0,
            ],
            "criticality": [
                0.30,
                0.50,
                0.80,
                1.00,
            ],
        }
    )


class TestMaintenancePriorityWeights:
    """Tests for maintenance-priority weights."""

    def test_default_weights_sum_to_one(self) -> None:
        weights = MaintenancePriorityWeights()

        total = (
            weights.risk_score
            + weights.failure_probability
            + weights.health_degradation
            + weights.criticality
        )

        assert total == pytest.approx(1.0)

    def test_accepts_custom_weights(self) -> None:
        weights = MaintenancePriorityWeights(
            risk_score=0.50,
            failure_probability=0.20,
            health_degradation=0.20,
            criticality=0.10,
        )

        assert weights.risk_score == pytest.approx(0.50)

    def test_rejects_negative_weight(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance priority weights must not be negative.",
        ):
            MaintenancePriorityWeights(
                risk_score=-0.10,
                failure_probability=0.40,
                health_degradation=0.40,
                criticality=0.30,
            )

    @pytest.mark.parametrize(
        "value",
        [
            math.inf,
            -math.inf,
            math.nan,
        ],
    )
    def test_rejects_non_finite_weight(
        self,
        value: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance priority weights must be finite.",
        ):
            MaintenancePriorityWeights(
                risk_score=value,
            )

    def test_rejects_weights_not_summing_to_one(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance priority weights must sum to 1.",
        ):
            MaintenancePriorityWeights(
                risk_score=0.50,
                failure_probability=0.30,
                health_degradation=0.30,
                criticality=0.10,
            )


class TestMaintenancePriorityResult:
    """Tests for maintenance-priority result validation."""

    def test_accepts_valid_result(self) -> None:
        result = MaintenancePriorityResult(
            equipment_id="INV-001",
            priority_score=0.75,
            priority_rank=1,
        )

        assert result.equipment_id == "INV-001"
        assert result.priority_score == pytest.approx(0.75)
        assert result.priority_rank == 1

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            MaintenancePriorityResult(
                equipment_id=" ",
                priority_score=0.50,
                priority_rank=1,
            )

    @pytest.mark.parametrize(
        "priority_score",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_priority_score(
        self,
        priority_score: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="priority_score must be between 0 and 1.",
        ):
            MaintenancePriorityResult(
                equipment_id="INV-001",
                priority_score=priority_score,
                priority_rank=1,
            )

    @pytest.mark.parametrize(
        "priority_rank",
        [
            0,
            -1,
        ],
    )
    def test_rejects_invalid_priority_rank(
        self,
        priority_rank: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="priority_rank must be greater than zero.",
        ):
            MaintenancePriorityResult(
                equipment_id="INV-001",
                priority_score=0.50,
                priority_rank=priority_rank,
            )


class TestCalculatePriorityScore:
    """Tests for individual maintenance-priority scoring."""

    def test_calculates_expected_score(self) -> None:
        result = calculate_priority_score(
            risk_score=0.50,
            failure_probability=0.40,
            health_score=60.0,
            criticality=0.80,
        )

        expected = 0.50 * 0.40 + 0.40 * 0.30 + 0.40 * 0.20 + 0.80 * 0.10

        assert result == pytest.approx(expected)

    def test_perfect_health_has_zero_health_degradation(self) -> None:
        result = calculate_priority_score(
            risk_score=0.0,
            failure_probability=0.0,
            health_score=100.0,
            criticality=0.0,
        )

        assert result == pytest.approx(0.0)

    def test_maximum_inputs_produce_maximum_score(self) -> None:
        result = calculate_priority_score(
            risk_score=1.0,
            failure_probability=1.0,
            health_score=0.0,
            criticality=1.0,
        )

        assert result == pytest.approx(1.0)

    def test_supports_custom_weights(self) -> None:
        weights = MaintenancePriorityWeights(
            risk_score=1.0,
            failure_probability=0.0,
            health_degradation=0.0,
            criticality=0.0,
        )

        result = calculate_priority_score(
            risk_score=0.75,
            failure_probability=1.0,
            health_score=0.0,
            criticality=1.0,
            weights=weights,
        )

        assert result == pytest.approx(0.75)

    @pytest.mark.parametrize(
        ("field_name", "invalid_value", "message"),
        [
            (
                "risk_score",
                -0.01,
                "risk_score must be between 0 and 1.",
            ),
            (
                "risk_score",
                1.01,
                "risk_score must be between 0 and 1.",
            ),
            (
                "failure_probability",
                -0.01,
                "failure_probability must be between 0 and 1.",
            ),
            (
                "failure_probability",
                1.01,
                "failure_probability must be between 0 and 1.",
            ),
            (
                "health_score",
                -0.01,
                "health_score must be between 0 and 100.",
            ),
            (
                "health_score",
                100.01,
                "health_score must be between 0 and 100.",
            ),
            (
                "criticality",
                -0.01,
                "criticality must be between 0 and 1.",
            ),
            (
                "criticality",
                1.01,
                "criticality must be between 0 and 1.",
            ),
        ],
    )
    def test_rejects_out_of_range_inputs(
        self,
        field_name: str,
        invalid_value: float,
        message: str,
    ) -> None:
        inputs = {
            "risk_score": 0.50,
            "failure_probability": 0.40,
            "health_score": 60.0,
            "criticality": 0.80,
        }

        inputs[field_name] = invalid_value

        with pytest.raises(
            ValueError,
            match=message,
        ):
            calculate_priority_score(**inputs)

    @pytest.mark.parametrize(
        ("field_name", "invalid_value"),
        [
            ("risk_score", math.nan),
            ("failure_probability", math.inf),
            ("health_score", -math.inf),
            ("criticality", math.nan),
        ],
    )
    def test_rejects_non_finite_inputs(
        self,
        field_name: str,
        invalid_value: float,
    ) -> None:
        inputs = {
            "risk_score": 0.50,
            "failure_probability": 0.40,
            "health_score": 60.0,
            "criticality": 0.80,
        }

        inputs[field_name] = invalid_value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            calculate_priority_score(**inputs)


class TestPrioritizeMaintenance:
    """Tests for batch maintenance prioritization."""

    def test_adds_priority_columns(self) -> None:
        result = prioritize_maintenance(frame=_frame())

        assert "priority_score" in result.columns
        assert "priority_rank" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _frame()

        result = prioritize_maintenance(frame=frame)

        assert len(result) == len(frame)

    def test_highest_risk_asset_ranks_first(self) -> None:
        result = prioritize_maintenance(frame=_frame())

        assert (
            result.loc[
                0,
                "equipment_id",
            ]
            == "INV-004"
        )

        assert (
            result.loc[
                0,
                "priority_rank",
            ]
            == 1
        )

    def test_returns_expected_order(self) -> None:
        result = prioritize_maintenance(frame=_frame())

        assert result["equipment_id"].tolist() == [
            "INV-004",
            "INV-003",
            "INV-002",
            "INV-001",
        ]

    def test_priority_scores_descend(self) -> None:
        result = prioritize_maintenance(frame=_frame())

        assert result["priority_score"].is_monotonic_decreasing

    def test_assigns_sequential_ranks(self) -> None:
        result = prioritize_maintenance(frame=_frame())

        assert result["priority_rank"].tolist() == [
            1,
            2,
            3,
            4,
        ]

    def test_priority_scores_are_within_range(self) -> None:
        result = prioritize_maintenance(frame=_frame())

        assert (
            result["priority_score"]
            .between(
                0.0,
                1.0,
            )
            .all()
        )

    def test_ties_are_broken_by_equipment_id(self) -> None:
        frame = pd.DataFrame(
            {
                "equipment_id": [
                    "INV-002",
                    "INV-001",
                ],
                "risk_score": [
                    0.50,
                    0.50,
                ],
                "failure_probability": [
                    0.50,
                    0.50,
                ],
                "health_score": [
                    50.0,
                    50.0,
                ],
                "criticality": [
                    0.50,
                    0.50,
                ],
            }
        )

        result = prioritize_maintenance(frame=frame)

        assert result["equipment_id"].tolist() == [
            "INV-001",
            "INV-002",
        ]

    def test_supports_custom_weights(self) -> None:
        weights = MaintenancePriorityWeights(
            risk_score=0.0,
            failure_probability=0.0,
            health_degradation=0.0,
            criticality=1.0,
        )

        result = prioritize_maintenance(
            frame=_frame(),
            weights=weights,
        )

        assert (
            result.loc[
                0,
                "equipment_id",
            ]
            == "INV-004"
        )

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        prioritize_maintenance(frame=frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance priority frame must not be empty.",
        ):
            prioritize_maintenance(frame=pd.DataFrame())

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["criticality"])

        with pytest.raises(
            ValueError,
            match=("Maintenance priority frame is missing required columns"),
        ):
            prioritize_maintenance(frame=frame)

    def test_rejects_blank_equipment_id(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "equipment_id",
        ] = " "

        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            prioritize_maintenance(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "equipment_id": "asset_id",
                "risk_score": "asset_risk",
                "failure_probability": "failure_risk",
                "health_score": "asset_health",
                "criticality": "asset_criticality",
            }
        )

        result = prioritize_maintenance(
            frame=frame,
            equipment_id_column="asset_id",
            risk_score_column="asset_risk",
            failure_probability_column="failure_risk",
            health_score_column="asset_health",
            criticality_column="asset_criticality",
        )

        assert "priority_score" in result.columns
        assert "priority_rank" in result.columns
