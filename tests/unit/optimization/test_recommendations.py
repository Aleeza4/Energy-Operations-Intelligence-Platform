"""Unit tests for EOIP optimization recommendation engine."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.optimization.recommendations import (
    OptimizationRecommendation,
    RecommendationType,
    generate_recommendation,
    generate_recommendations,
)


def _frame() -> pd.DataFrame:
    """Return deterministic recommendation inputs."""
    return pd.DataFrame(
        {
            "equipment_id": [
                "INV-001",
                "INV-002",
                "INV-003",
                "INV-004",
            ],
            "risk_score": [
                0.80,
                0.20,
                0.40,
                0.10,
            ],
            "recoverable_energy_kwh": [
                500.0,
                300.0,
                0.0,
                0.0,
            ],
            "economically_justified": [
                True,
                False,
                False,
                False,
            ],
            "expected_benefit": [
                10000.0,
                2500.0,
                1000.0,
                0.0,
            ],
        }
    )


class TestRecommendationType:
    """Tests for recommendation enum values."""

    def test_values(self) -> None:
        assert RecommendationType.MAINTENANCE.value == "maintenance"
        assert RecommendationType.PERFORMANCE_RECOVERY.value == "performance_recovery"
        assert RecommendationType.MONITOR.value == "monitor"
        assert RecommendationType.NO_ACTION.value == "no_action"


class TestOptimizationRecommendation:
    """Tests for optimization recommendation validation."""

    def test_accepts_valid_recommendation(self) -> None:
        result = OptimizationRecommendation(
            equipment_id="INV-001",
            recommendation_type=RecommendationType.MAINTENANCE,
            action="Schedule preventive maintenance.",
            rationale="Elevated risk.",
            expected_benefit=5000.0,
        )

        assert result.equipment_id == "INV-001"
        assert result.recommendation_type is RecommendationType.MAINTENANCE
        assert result.expected_benefit == pytest.approx(5000.0)

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            OptimizationRecommendation(
                equipment_id=" ",
                recommendation_type=RecommendationType.MONITOR,
                action="Monitor.",
                rationale="Risk detected.",
                expected_benefit=0.0,
            )

    def test_rejects_empty_action(self) -> None:
        with pytest.raises(
            ValueError,
            match="action must not be empty.",
        ):
            OptimizationRecommendation(
                equipment_id="INV-001",
                recommendation_type=RecommendationType.MONITOR,
                action=" ",
                rationale="Risk detected.",
                expected_benefit=0.0,
            )

    def test_rejects_empty_rationale(self) -> None:
        with pytest.raises(
            ValueError,
            match="rationale must not be empty.",
        ):
            OptimizationRecommendation(
                equipment_id="INV-001",
                recommendation_type=RecommendationType.MONITOR,
                action="Monitor.",
                rationale=" ",
                expected_benefit=0.0,
            )

    @pytest.mark.parametrize(
        "value",
        [
            math.nan,
            math.inf,
            -math.inf,
        ],
    )
    def test_rejects_non_finite_expected_benefit(
        self,
        value: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="expected_benefit must be finite.",
        ):
            OptimizationRecommendation(
                equipment_id="INV-001",
                recommendation_type=RecommendationType.MONITOR,
                action="Monitor.",
                rationale="Risk detected.",
                expected_benefit=value,
            )

    def test_rejects_negative_expected_benefit(self) -> None:
        with pytest.raises(
            ValueError,
            match="expected_benefit must not be negative.",
        ):
            OptimizationRecommendation(
                equipment_id="INV-001",
                recommendation_type=RecommendationType.MONITOR,
                action="Monitor.",
                rationale="Risk detected.",
                expected_benefit=-1.0,
            )


class TestGenerateRecommendation:
    """Tests for individual recommendation generation."""

    def test_generates_maintenance_recommendation(self) -> None:
        result = generate_recommendation(
            equipment_id="INV-001",
            risk_score=0.80,
            recoverable_energy_kwh=500.0,
            economically_justified=True,
            expected_benefit=10000.0,
        )

        assert result.recommendation_type is RecommendationType.MAINTENANCE
        assert result.action == "Schedule preventive maintenance."

    def test_maintenance_takes_precedence_over_recovery(self) -> None:
        result = generate_recommendation(
            equipment_id="INV-001",
            risk_score=0.80,
            recoverable_energy_kwh=1000.0,
            economically_justified=True,
            expected_benefit=10000.0,
        )

        assert result.recommendation_type is RecommendationType.MAINTENANCE

    def test_generates_performance_recovery_recommendation(
        self,
    ) -> None:
        result = generate_recommendation(
            equipment_id="INV-002",
            risk_score=0.20,
            recoverable_energy_kwh=300.0,
            economically_justified=False,
            expected_benefit=2500.0,
        )

        assert result.recommendation_type is RecommendationType.PERFORMANCE_RECOVERY

    def test_generates_monitor_recommendation(self) -> None:
        result = generate_recommendation(
            equipment_id="INV-003",
            risk_score=0.40,
            recoverable_energy_kwh=0.0,
            economically_justified=False,
            expected_benefit=1000.0,
        )

        assert result.recommendation_type is RecommendationType.MONITOR

    def test_generates_no_action_recommendation(self) -> None:
        result = generate_recommendation(
            equipment_id="INV-004",
            risk_score=0.10,
            recoverable_energy_kwh=0.0,
            economically_justified=False,
            expected_benefit=0.0,
        )

        assert result.recommendation_type is RecommendationType.NO_ACTION

    def test_risk_boundary_at_half_is_maintenance_when_justified(
        self,
    ) -> None:
        result = generate_recommendation(
            equipment_id="INV-001",
            risk_score=0.50,
            recoverable_energy_kwh=0.0,
            economically_justified=True,
            expected_benefit=1000.0,
        )

        assert result.recommendation_type is RecommendationType.MAINTENANCE

    def test_monitor_boundary_at_quarter(self) -> None:
        result = generate_recommendation(
            equipment_id="INV-001",
            risk_score=0.25,
            recoverable_energy_kwh=0.0,
            economically_justified=False,
            expected_benefit=0.0,
        )

        assert result.recommendation_type is RecommendationType.MONITOR

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            generate_recommendation(
                equipment_id=" ",
                risk_score=0.50,
                recoverable_energy_kwh=100.0,
                economically_justified=True,
                expected_benefit=1000.0,
            )

    @pytest.mark.parametrize(
        "risk_score",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_risk_score(
        self,
        risk_score: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="risk_score must be between 0 and 1.",
        ):
            generate_recommendation(
                equipment_id="INV-001",
                risk_score=risk_score,
                recoverable_energy_kwh=100.0,
                economically_justified=True,
                expected_benefit=1000.0,
            )

    def test_rejects_negative_recoverable_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match="recoverable_energy_kwh must not be negative.",
        ):
            generate_recommendation(
                equipment_id="INV-001",
                risk_score=0.50,
                recoverable_energy_kwh=-1.0,
                economically_justified=True,
                expected_benefit=1000.0,
            )

    def test_rejects_negative_expected_benefit(self) -> None:
        with pytest.raises(
            ValueError,
            match="expected_benefit must not be negative.",
        ):
            generate_recommendation(
                equipment_id="INV-001",
                risk_score=0.50,
                recoverable_energy_kwh=100.0,
                economically_justified=True,
                expected_benefit=-1.0,
            )

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("risk_score", math.nan),
            ("recoverable_energy_kwh", math.inf),
            ("expected_benefit", -math.inf),
        ],
    )
    def test_rejects_non_finite_values(
        self,
        field_name: str,
        value: float,
    ) -> None:
        inputs = {
            "risk_score": 0.50,
            "recoverable_energy_kwh": 100.0,
            "expected_benefit": 1000.0,
        }

        inputs[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            generate_recommendation(
                equipment_id="INV-001",
                economically_justified=True,
                **inputs,
            )


class TestGenerateRecommendations:
    """Tests for batch recommendation generation."""

    def test_adds_recommendation_columns(self) -> None:
        result = generate_recommendations(frame=_frame())

        assert "recommendation_type" in result.columns
        assert "recommended_action" in result.columns
        assert "recommendation_rationale" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _frame()

        result = generate_recommendations(frame=frame)

        assert len(result) == len(frame)

    def test_generates_expected_recommendation_types(self) -> None:
        result = generate_recommendations(frame=_frame())

        assert result["recommendation_type"].tolist() == [
            "maintenance",
            "performance_recovery",
            "monitor",
            "no_action",
        ]

    def test_generates_non_empty_actions(self) -> None:
        result = generate_recommendations(frame=_frame())

        assert result["recommended_action"].str.strip().ne("").all()

    def test_generates_non_empty_rationales(self) -> None:
        result = generate_recommendations(frame=_frame())

        assert result["recommendation_rationale"].str.strip().ne("").all()

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        generate_recommendations(frame=frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Recommendation frame must not be empty.",
        ):
            generate_recommendations(frame=pd.DataFrame())

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["risk_score"])

        with pytest.raises(
            ValueError,
            match=("Recommendation frame is missing required columns"),
        ):
            generate_recommendations(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "equipment_id": "asset_id",
                "risk_score": "asset_risk",
                "recoverable_energy_kwh": "recoverable",
                "economically_justified": "justified",
                "expected_benefit": "benefit",
            }
        )

        result = generate_recommendations(
            frame=frame,
            equipment_id_column="asset_id",
            risk_score_column="asset_risk",
            recoverable_energy_column="recoverable",
            economically_justified_column="justified",
            expected_benefit_column="benefit",
        )

        assert "recommendation_type" in result.columns
        assert "recommended_action" in result.columns
        assert "recommendation_rationale" in result.columns
