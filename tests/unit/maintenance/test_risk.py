"""Unit tests for EOIP predictive-maintenance risk classification."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.maintenance.risk import (
    MaintenanceRiskLevel,
    MaintenanceRiskResult,
    classify_equipment_risk,
    classify_equipment_risks,
    classify_risk_score,
)


def _risk_frame() -> pd.DataFrame:
    """Return deterministic maintenance risk inputs."""
    return pd.DataFrame(
        {
            "equipment_id": [
                "INV-001",
                "INV-002",
                "INV-003",
                "INV-004",
            ],
            "health_score": [
                95.0,
                70.0,
                40.0,
                10.0,
            ],
            "failure_probability": [
                0.05,
                0.35,
                0.65,
                0.95,
            ],
        }
    )


class TestMaintenanceRiskLevel:
    """Tests for maintenance risk levels."""

    def test_values(self) -> None:
        assert MaintenanceRiskLevel.LOW.value == "low"
        assert MaintenanceRiskLevel.MODERATE.value == "moderate"
        assert MaintenanceRiskLevel.HIGH.value == "high"
        assert MaintenanceRiskLevel.CRITICAL.value == "critical"


class TestMaintenanceRiskResult:
    """Tests for maintenance risk result validation."""

    def test_accepts_valid_result(self) -> None:
        result = MaintenanceRiskResult(
            equipment_id="INV-001",
            health_score=80.0,
            failure_probability=0.20,
            risk_score=0.20,
            risk_level=MaintenanceRiskLevel.LOW,
        )

        assert result.equipment_id == "INV-001"
        assert result.health_score == pytest.approx(80.0)
        assert result.failure_probability == pytest.approx(0.20)
        assert result.risk_score == pytest.approx(0.20)
        assert result.risk_level is MaintenanceRiskLevel.LOW

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            MaintenanceRiskResult(
                equipment_id=" ",
                health_score=80.0,
                failure_probability=0.20,
                risk_score=0.20,
                risk_level=MaintenanceRiskLevel.LOW,
            )

    @pytest.mark.parametrize(
        "health_score",
        [
            -0.01,
            100.01,
        ],
    )
    def test_rejects_invalid_health_score(
        self,
        health_score: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="health_score must be between 0 and 100.",
        ):
            MaintenanceRiskResult(
                equipment_id="INV-001",
                health_score=health_score,
                failure_probability=0.20,
                risk_score=0.20,
                risk_level=MaintenanceRiskLevel.LOW,
            )

    @pytest.mark.parametrize(
        "failure_probability",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_failure_probability(
        self,
        failure_probability: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="failure_probability must be between 0 and 1.",
        ):
            MaintenanceRiskResult(
                equipment_id="INV-001",
                health_score=80.0,
                failure_probability=failure_probability,
                risk_score=0.20,
                risk_level=MaintenanceRiskLevel.LOW,
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
            MaintenanceRiskResult(
                equipment_id="INV-001",
                health_score=80.0,
                failure_probability=0.20,
                risk_score=risk_score,
                risk_level=MaintenanceRiskLevel.LOW,
            )


class TestClassifyRiskScore:
    """Tests for normalized risk-score classification."""

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (0.00, MaintenanceRiskLevel.LOW),
            (0.10, MaintenanceRiskLevel.LOW),
            (0.2499, MaintenanceRiskLevel.LOW),
            (0.25, MaintenanceRiskLevel.MODERATE),
            (0.40, MaintenanceRiskLevel.MODERATE),
            (0.4999, MaintenanceRiskLevel.MODERATE),
            (0.50, MaintenanceRiskLevel.HIGH),
            (0.60, MaintenanceRiskLevel.HIGH),
            (0.7499, MaintenanceRiskLevel.HIGH),
            (0.75, MaintenanceRiskLevel.CRITICAL),
            (0.90, MaintenanceRiskLevel.CRITICAL),
            (1.00, MaintenanceRiskLevel.CRITICAL),
        ],
    )
    def test_classifies_thresholds(
        self,
        score: float,
        expected: MaintenanceRiskLevel,
    ) -> None:
        assert classify_risk_score(score) is expected

    @pytest.mark.parametrize(
        "score",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_out_of_range_score(
        self,
        score: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="risk_score must be between 0 and 1.",
        ):
            classify_risk_score(score)

    @pytest.mark.parametrize(
        "score",
        [
            math.nan,
            math.inf,
            -math.inf,
        ],
    )
    def test_rejects_non_finite_score(
        self,
        score: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="risk_score must be finite.",
        ):
            classify_risk_score(score)


class TestClassifyEquipmentRisk:
    """Tests for individual equipment risk classification."""

    def test_calculates_expected_risk_score(self) -> None:
        result = classify_equipment_risk(
            equipment_id="INV-001",
            health_score=50.0,
            failure_probability=0.50,
        )

        expected = (0.50 * 0.40) + (0.50 * 0.60)

        assert result.risk_score == pytest.approx(expected)
        assert result.risk_level is MaintenanceRiskLevel.HIGH

    def test_healthy_low_probability_asset_is_low_risk(
        self,
    ) -> None:
        result = classify_equipment_risk(
            equipment_id="INV-001",
            health_score=100.0,
            failure_probability=0.0,
        )

        assert result.risk_score == pytest.approx(0.0)
        assert result.risk_level is MaintenanceRiskLevel.LOW

    def test_failed_health_high_probability_asset_is_critical(
        self,
    ) -> None:
        result = classify_equipment_risk(
            equipment_id="INV-001",
            health_score=0.0,
            failure_probability=1.0,
        )

        assert result.risk_score == pytest.approx(1.0)
        assert result.risk_level is MaintenanceRiskLevel.CRITICAL

    def test_failure_probability_has_default_sixty_percent_weight(
        self,
    ) -> None:
        result = classify_equipment_risk(
            equipment_id="INV-001",
            health_score=100.0,
            failure_probability=1.0,
        )

        assert result.risk_score == pytest.approx(0.60)
        assert result.risk_level is MaintenanceRiskLevel.HIGH

    def test_supports_custom_weights(self) -> None:
        result = classify_equipment_risk(
            equipment_id="INV-001",
            health_score=50.0,
            failure_probability=1.0,
            health_weight=1.0,
            failure_probability_weight=0.0,
        )

        assert result.risk_score == pytest.approx(0.50)
        assert result.risk_level is MaintenanceRiskLevel.HIGH

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            classify_equipment_risk(
                equipment_id=" ",
                health_score=80.0,
                failure_probability=0.20,
            )

    @pytest.mark.parametrize(
        "health_score",
        [
            -0.01,
            100.01,
        ],
    )
    def test_rejects_invalid_health_score(
        self,
        health_score: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="health_score must be between 0 and 100.",
        ):
            classify_equipment_risk(
                equipment_id="INV-001",
                health_score=health_score,
                failure_probability=0.20,
            )

    @pytest.mark.parametrize(
        "failure_probability",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_failure_probability(
        self,
        failure_probability: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="failure_probability must be between 0 and 1.",
        ):
            classify_equipment_risk(
                equipment_id="INV-001",
                health_score=80.0,
                failure_probability=failure_probability,
            )

    def test_rejects_negative_health_weight(self) -> None:
        with pytest.raises(
            ValueError,
            match="health_weight must not be negative.",
        ):
            classify_equipment_risk(
                equipment_id="INV-001",
                health_score=80.0,
                failure_probability=0.20,
                health_weight=-0.10,
                failure_probability_weight=1.10,
            )

    def test_rejects_negative_failure_probability_weight(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=("failure_probability_weight must not be negative."),
        ):
            classify_equipment_risk(
                equipment_id="INV-001",
                health_score=80.0,
                failure_probability=0.20,
                health_weight=1.10,
                failure_probability_weight=-0.10,
            )

    def test_rejects_weights_not_summing_to_one(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Risk classification weights must sum to 1.",
        ):
            classify_equipment_risk(
                equipment_id="INV-001",
                health_score=80.0,
                failure_probability=0.20,
                health_weight=0.50,
                failure_probability_weight=0.60,
            )

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("health_score", math.nan),
            ("failure_probability", math.inf),
            ("health_weight", -math.inf),
            ("failure_probability_weight", math.nan),
        ],
    )
    def test_rejects_non_finite_values(
        self,
        field_name: str,
        value: float,
    ) -> None:
        arguments = {
            "equipment_id": "INV-001",
            "health_score": 80.0,
            "failure_probability": 0.20,
            "health_weight": 0.40,
            "failure_probability_weight": 0.60,
        }

        arguments[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            classify_equipment_risk(**arguments)


class TestClassifyEquipmentRisks:
    """Tests for batch equipment risk classification."""

    def test_adds_risk_columns(self) -> None:
        result = classify_equipment_risks(frame=_risk_frame())

        assert "risk_score" in result.columns
        assert "risk_level" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _risk_frame()

        result = classify_equipment_risks(frame=frame)

        assert len(result) == len(frame)

    def test_preserves_equipment_ids(self) -> None:
        frame = _risk_frame()

        result = classify_equipment_risks(frame=frame)

        assert result["equipment_id"].tolist() == (frame["equipment_id"].tolist())

    def test_risk_scores_are_valid(self) -> None:
        result = classify_equipment_risks(frame=_risk_frame())

        assert (
            result["risk_score"]
            .between(
                0.0,
                1.0,
            )
            .all()
        )

    def test_returns_expected_risk_order(self) -> None:
        result = classify_equipment_risks(frame=_risk_frame())

        scores = result.set_index("equipment_id")["risk_score"]

        assert (
            scores["INV-001"]
            < scores["INV-002"]
            < scores["INV-003"]
            < scores["INV-004"]
        )

    def test_returns_expected_risk_levels(self) -> None:
        result = classify_equipment_risks(frame=_risk_frame())

        assert result["risk_level"].tolist() == [
            "low",
            "moderate",
            "high",
            "critical",
        ]

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _risk_frame()
        original = frame.copy(deep=True)

        classify_equipment_risks(frame=frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Maintenance risk frame must not be empty.",
        ):
            classify_equipment_risks(frame=pd.DataFrame())

    def test_rejects_missing_required_column(self) -> None:
        frame = _risk_frame().drop(columns=["health_score"])

        with pytest.raises(
            ValueError,
            match=("Maintenance risk frame is missing required columns"),
        ):
            classify_equipment_risks(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _risk_frame().rename(
            columns={
                "equipment_id": "asset_id",
                "health_score": "asset_health",
                "failure_probability": "failure_risk",
            }
        )

        result = classify_equipment_risks(
            frame=frame,
            equipment_id_column="asset_id",
            health_score_column="asset_health",
            failure_probability_column="failure_risk",
        )

        assert "risk_score" in result.columns
        assert "risk_level" in result.columns
