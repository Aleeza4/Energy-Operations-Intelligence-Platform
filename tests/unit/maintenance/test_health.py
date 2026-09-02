"""Unit tests for EOIP predictive-maintenance equipment health scoring."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.maintenance.health import (
    EquipmentHealthResult,
    HealthScoreWeights,
    calculate_equipment_health_score,
    calculate_health_scores,
)


def _health_frame() -> pd.DataFrame:
    """Return deterministic equipment health inputs."""
    return pd.DataFrame(
        {
            "equipment_id": [
                "INV-001",
                "INV-002",
                "INV-003",
            ],
            "failure_probability": [
                0.10,
                0.50,
                0.90,
            ],
            "anomaly_rate": [
                0.10,
                0.40,
                0.80,
            ],
            "alarm_burden": [
                0.05,
                0.50,
                0.90,
            ],
            "temperature_stress": [
                0.10,
                0.60,
                0.90,
            ],
            "performance_loss": [
                0.05,
                0.40,
                0.85,
            ],
        }
    )


class TestHealthScoreWeights:
    """Tests for equipment health score weights."""

    def test_default_weights_sum_to_one(self) -> None:
        weights = HealthScoreWeights()

        total = (
            weights.failure_probability
            + weights.anomaly_rate
            + weights.alarm_burden
            + weights.temperature_stress
            + weights.performance_loss
        )

        assert total == pytest.approx(1.0)

    def test_accepts_valid_custom_weights(self) -> None:
        weights = HealthScoreWeights(
            failure_probability=0.40,
            anomaly_rate=0.20,
            alarm_burden=0.10,
            temperature_stress=0.10,
            performance_loss=0.20,
        )

        assert weights.failure_probability == pytest.approx(0.40)

    def test_rejects_negative_weight(self) -> None:
        with pytest.raises(
            ValueError,
            match="Health score weights must not be negative.",
        ):
            HealthScoreWeights(
                failure_probability=-0.10,
                anomaly_rate=0.30,
                alarm_burden=0.25,
                temperature_stress=0.25,
                performance_loss=0.30,
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
            match="Health score weights must be finite.",
        ):
            HealthScoreWeights(
                failure_probability=value,
            )

    def test_rejects_weights_not_summing_to_one(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Health score weights must sum to 1.",
        ):
            HealthScoreWeights(
                failure_probability=0.50,
                anomaly_rate=0.20,
                alarm_burden=0.20,
                temperature_stress=0.20,
                performance_loss=0.20,
            )


class TestEquipmentHealthResult:
    """Tests for equipment health result validation."""

    def test_accepts_valid_result(self) -> None:
        result = EquipmentHealthResult(
            equipment_id="INV-001",
            health_score=80.0,
            degradation_score=0.20,
        )

        assert result.equipment_id == "INV-001"
        assert result.health_score == pytest.approx(80.0)
        assert result.degradation_score == pytest.approx(0.20)

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            EquipmentHealthResult(
                equipment_id=" ",
                health_score=80.0,
                degradation_score=0.20,
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
            EquipmentHealthResult(
                equipment_id="INV-001",
                health_score=health_score,
                degradation_score=0.20,
            )

    @pytest.mark.parametrize(
        "degradation_score",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_degradation_score(
        self,
        degradation_score: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=("degradation_score must be between 0 and 1."),
        ):
            EquipmentHealthResult(
                equipment_id="INV-001",
                health_score=80.0,
                degradation_score=degradation_score,
            )


class TestCalculateEquipmentHealthScore:
    """Tests for individual equipment health scoring."""

    def test_perfect_health_when_all_inputs_are_zero(
        self,
    ) -> None:
        result = calculate_equipment_health_score(
            equipment_id="INV-001",
            failure_probability=0.0,
            anomaly_rate=0.0,
            alarm_burden=0.0,
            temperature_stress=0.0,
            performance_loss=0.0,
        )

        assert result.degradation_score == pytest.approx(0.0)
        assert result.health_score == pytest.approx(100.0)

    def test_zero_health_when_all_inputs_are_one(
        self,
    ) -> None:
        result = calculate_equipment_health_score(
            equipment_id="INV-001",
            failure_probability=1.0,
            anomaly_rate=1.0,
            alarm_burden=1.0,
            temperature_stress=1.0,
            performance_loss=1.0,
        )

        assert result.degradation_score == pytest.approx(1.0)
        assert result.health_score == pytest.approx(0.0)

    def test_calculates_weighted_score_correctly(
        self,
    ) -> None:
        result = calculate_equipment_health_score(
            equipment_id="INV-001",
            failure_probability=0.50,
            anomaly_rate=0.25,
            alarm_burden=0.20,
            temperature_stress=0.10,
            performance_loss=0.40,
        )

        expected_degradation = (
            0.50 * 0.35 + 0.25 * 0.20 + 0.20 * 0.15 + 0.10 * 0.15 + 0.40 * 0.15
        )

        expected_health = 100.0 * (1.0 - expected_degradation)

        assert result.degradation_score == pytest.approx(expected_degradation)

        assert result.health_score == pytest.approx(expected_health)
        assert dict(result.component_contributions)[
            "failure_probability"
        ] == pytest.approx(0.175)

    def test_supports_custom_weights(self) -> None:
        weights = HealthScoreWeights(
            failure_probability=1.0,
            anomaly_rate=0.0,
            alarm_burden=0.0,
            temperature_stress=0.0,
            performance_loss=0.0,
        )

        result = calculate_equipment_health_score(
            equipment_id="INV-001",
            failure_probability=0.25,
            anomaly_rate=1.0,
            alarm_burden=1.0,
            temperature_stress=1.0,
            performance_loss=1.0,
            weights=weights,
        )

        assert result.degradation_score == pytest.approx(0.25)

        assert result.health_score == pytest.approx(75.0)

    def test_includes_confidence_and_historical_trend(self) -> None:
        result = calculate_equipment_health_score(
            equipment_id="INV-001",
            failure_probability=0.40,
            anomaly_rate=0.30,
            alarm_burden=0.20,
            temperature_stress=0.15,
            performance_loss=0.10,
            history=[90.0, 85.0, 70.0],
        )

        assert 0.0 <= result.confidence_score <= 1.0
        assert result.trend_direction in {"improving", "stable", "degrading"}
        assert -1.0 <= result.trend_score <= 1.0

    def test_higher_degradation_reduces_health(
        self,
    ) -> None:
        healthy = calculate_equipment_health_score(
            equipment_id="INV-001",
            failure_probability=0.10,
            anomaly_rate=0.10,
            alarm_burden=0.10,
            temperature_stress=0.10,
            performance_loss=0.10,
        )

        degraded = calculate_equipment_health_score(
            equipment_id="INV-002",
            failure_probability=0.80,
            anomaly_rate=0.80,
            alarm_burden=0.80,
            temperature_stress=0.80,
            performance_loss=0.80,
        )

        assert degraded.health_score < healthy.health_score

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            calculate_equipment_health_score(
                equipment_id=" ",
                failure_probability=0.1,
                anomaly_rate=0.1,
                alarm_burden=0.1,
                temperature_stress=0.1,
                performance_loss=0.1,
            )

    @pytest.mark.parametrize(
        ("field_name", "invalid_value"),
        [
            ("failure_probability", -0.01),
            ("failure_probability", 1.01),
            ("anomaly_rate", -0.01),
            ("anomaly_rate", 1.01),
            ("alarm_burden", -0.01),
            ("alarm_burden", 1.01),
            ("temperature_stress", -0.01),
            ("temperature_stress", 1.01),
            ("performance_loss", -0.01),
            ("performance_loss", 1.01),
        ],
    )
    def test_rejects_values_outside_unit_interval(
        self,
        field_name: str,
        invalid_value: float,
    ) -> None:
        inputs = {
            "failure_probability": 0.1,
            "anomaly_rate": 0.1,
            "alarm_burden": 0.1,
            "temperature_stress": 0.1,
            "performance_loss": 0.1,
        }

        inputs[field_name] = invalid_value

        with pytest.raises(
            ValueError,
            match=(f"{field_name} must be between 0 and 1."),
        ):
            calculate_equipment_health_score(
                equipment_id="INV-001",
                **inputs,
            )

    @pytest.mark.parametrize(
        ("field_name", "invalid_value"),
        [
            ("failure_probability", math.nan),
            ("anomaly_rate", math.inf),
            ("alarm_burden", -math.inf),
            ("temperature_stress", math.nan),
            ("performance_loss", math.inf),
        ],
    )
    def test_rejects_non_finite_inputs(
        self,
        field_name: str,
        invalid_value: float,
    ) -> None:
        inputs = {
            "failure_probability": 0.1,
            "anomaly_rate": 0.1,
            "alarm_burden": 0.1,
            "temperature_stress": 0.1,
            "performance_loss": 0.1,
        }

        inputs[field_name] = invalid_value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            calculate_equipment_health_score(
                equipment_id="INV-001",
                **inputs,
            )


class TestCalculateHealthScores:
    """Tests for batch equipment health scoring."""

    def test_adds_health_columns(self) -> None:
        result = calculate_health_scores(frame=_health_frame())

        assert "health_score" in result.columns
        assert "degradation_score" in result.columns
        assert "failure_probability_contribution" in result.columns
        contribution_columns = [
            column for column in result if column.endswith("_contribution")
        ]
        assert result[contribution_columns].sum(axis=1).to_numpy() == pytest.approx(
            result["degradation_score"].to_numpy()
        )

    def test_returns_one_row_per_equipment(self) -> None:
        frame = _health_frame()

        result = calculate_health_scores(frame=frame)

        assert len(result) == len(frame)

    def test_preserves_equipment_ids(self) -> None:
        frame = _health_frame()

        result = calculate_health_scores(frame=frame)

        assert result["equipment_id"].tolist() == (frame["equipment_id"].tolist())

    def test_scores_remain_within_valid_ranges(
        self,
    ) -> None:
        result = calculate_health_scores(frame=_health_frame())

        assert (
            result["health_score"]
            .between(
                0.0,
                100.0,
            )
            .all()
        )

        assert (
            result["degradation_score"]
            .between(
                0.0,
                1.0,
            )
            .all()
        )

        assert "confidence_score" in result.columns
        assert "trend_direction" in result.columns

    def test_more_degraded_equipment_has_lower_health(
        self,
    ) -> None:
        result = calculate_health_scores(frame=_health_frame())

        scores = result.set_index("equipment_id")["health_score"]

        assert scores["INV-001"] > scores["INV-002"] > scores["INV-003"]

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _health_frame()
        original = frame.copy(deep=True)

        calculate_health_scores(frame=frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Equipment health frame must not be empty."),
        ):
            calculate_health_scores(frame=pd.DataFrame())

    def test_rejects_missing_required_column(
        self,
    ) -> None:
        frame = _health_frame().drop(columns=["anomaly_rate"])

        with pytest.raises(
            ValueError,
            match=("Equipment health frame is missing " "required columns"),
        ):
            calculate_health_scores(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _health_frame().rename(
            columns={
                "equipment_id": "asset_id",
                "failure_probability": "failure_risk",
                "anomaly_rate": "anomaly_risk",
                "alarm_burden": "alarm_risk",
                "temperature_stress": "thermal_risk",
                "performance_loss": "loss_risk",
            }
        )

        result = calculate_health_scores(
            frame=frame,
            equipment_id_column="asset_id",
            failure_probability_column="failure_risk",
            anomaly_rate_column="anomaly_risk",
            alarm_burden_column="alarm_risk",
            temperature_stress_column="thermal_risk",
            performance_loss_column="loss_risk",
        )

        assert "health_score" in result.columns
        assert "degradation_score" in result.columns
