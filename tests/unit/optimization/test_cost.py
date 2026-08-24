"""Unit tests for EOIP cost optimization."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.optimization.cost import (
    CostOptimizationResult,
    optimize_cost,
    optimize_costs,
)


def _frame() -> pd.DataFrame:
    """Return deterministic cost-optimization inputs."""
    return pd.DataFrame(
        {
            "equipment_id": [
                "INV-001",
                "INV-002",
                "INV-003",
            ],
            "intervention_cost": [
                1000.0,
                5000.0,
                2000.0,
            ],
            "failure_probability": [
                0.80,
                0.20,
                0.60,
            ],
            "failure_cost": [
                5000.0,
                10000.0,
                4000.0,
            ],
            "prevention_effectiveness": [
                1.0,
                0.80,
                0.50,
            ],
        }
    )


class TestCostOptimizationResult:
    """Tests for cost-optimization result validation."""

    def test_accepts_valid_result(self) -> None:
        result = CostOptimizationResult(
            equipment_id="INV-001",
            intervention_cost=1000.0,
            expected_loss_avoided=4000.0,
            net_benefit=3000.0,
            benefit_cost_ratio=4.0,
            should_intervene=True,
        )

        assert result.equipment_id == "INV-001"
        assert result.intervention_cost == pytest.approx(1000.0)
        assert result.expected_loss_avoided == pytest.approx(4000.0)
        assert result.net_benefit == pytest.approx(3000.0)
        assert result.benefit_cost_ratio == pytest.approx(4.0)
        assert result.should_intervene is True

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            CostOptimizationResult(
                equipment_id=" ",
                intervention_cost=1000.0,
                expected_loss_avoided=2000.0,
                net_benefit=1000.0,
                benefit_cost_ratio=2.0,
                should_intervene=True,
            )

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("intervention_cost", math.nan),
            ("expected_loss_avoided", math.inf),
            ("net_benefit", -math.inf),
            ("benefit_cost_ratio", math.nan),
        ],
    )
    def test_rejects_non_finite_values(
        self,
        field_name: str,
        value: float,
    ) -> None:
        values = {
            "intervention_cost": 1000.0,
            "expected_loss_avoided": 2000.0,
            "net_benefit": 1000.0,
            "benefit_cost_ratio": 2.0,
        }

        values[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            CostOptimizationResult(
                equipment_id="INV-001",
                should_intervene=True,
                **values,
            )

    def test_rejects_negative_intervention_cost(self) -> None:
        with pytest.raises(
            ValueError,
            match="intervention_cost must not be negative.",
        ):
            CostOptimizationResult(
                equipment_id="INV-001",
                intervention_cost=-1.0,
                expected_loss_avoided=1000.0,
                net_benefit=1001.0,
                benefit_cost_ratio=1.0,
                should_intervene=True,
            )

    def test_rejects_negative_expected_loss_avoided(self) -> None:
        with pytest.raises(
            ValueError,
            match="expected_loss_avoided must not be negative.",
        ):
            CostOptimizationResult(
                equipment_id="INV-001",
                intervention_cost=1000.0,
                expected_loss_avoided=-1.0,
                net_benefit=-1001.0,
                benefit_cost_ratio=0.0,
                should_intervene=False,
            )

    def test_rejects_negative_benefit_cost_ratio(self) -> None:
        with pytest.raises(
            ValueError,
            match="benefit_cost_ratio must not be negative.",
        ):
            CostOptimizationResult(
                equipment_id="INV-001",
                intervention_cost=1000.0,
                expected_loss_avoided=500.0,
                net_benefit=-500.0,
                benefit_cost_ratio=-0.5,
                should_intervene=False,
            )


class TestOptimizeCost:
    """Tests for individual cost optimization."""

    def test_calculates_expected_loss_avoided(self) -> None:
        result = optimize_cost(
            equipment_id="INV-001",
            intervention_cost=1000.0,
            failure_probability=0.80,
            failure_cost=5000.0,
            prevention_effectiveness=0.50,
        )

        assert result.expected_loss_avoided == pytest.approx(2000.0)

    def test_calculates_net_benefit(self) -> None:
        result = optimize_cost(
            equipment_id="INV-001",
            intervention_cost=1000.0,
            failure_probability=0.80,
            failure_cost=5000.0,
            prevention_effectiveness=0.50,
        )

        assert result.net_benefit == pytest.approx(1000.0)

    def test_calculates_benefit_cost_ratio(self) -> None:
        result = optimize_cost(
            equipment_id="INV-001",
            intervention_cost=1000.0,
            failure_probability=0.80,
            failure_cost=5000.0,
            prevention_effectiveness=0.50,
        )

        assert result.benefit_cost_ratio == pytest.approx(2.0)

    def test_should_intervene_when_net_benefit_positive(self) -> None:
        result = optimize_cost(
            equipment_id="INV-001",
            intervention_cost=1000.0,
            failure_probability=0.80,
            failure_cost=5000.0,
        )

        assert result.should_intervene is True

    def test_should_not_intervene_when_net_benefit_negative(
        self,
    ) -> None:
        result = optimize_cost(
            equipment_id="INV-001",
            intervention_cost=5000.0,
            failure_probability=0.20,
            failure_cost=10000.0,
        )

        assert result.net_benefit == pytest.approx(-3000.0)
        assert result.should_intervene is False

    def test_break_even_is_not_intervention(self) -> None:
        result = optimize_cost(
            equipment_id="INV-001",
            intervention_cost=1000.0,
            failure_probability=0.50,
            failure_cost=2000.0,
        )

        assert result.net_benefit == pytest.approx(0.0)
        assert result.should_intervene is False

    def test_zero_prevention_effectiveness(self) -> None:
        result = optimize_cost(
            equipment_id="INV-001",
            intervention_cost=1000.0,
            failure_probability=1.0,
            failure_cost=10000.0,
            prevention_effectiveness=0.0,
        )

        assert result.expected_loss_avoided == pytest.approx(0.0)
        assert result.net_benefit == pytest.approx(-1000.0)
        assert result.benefit_cost_ratio == pytest.approx(0.0)

    def test_zero_intervention_cost_and_zero_benefit(self) -> None:
        result = optimize_cost(
            equipment_id="INV-001",
            intervention_cost=0.0,
            failure_probability=0.0,
            failure_cost=10000.0,
        )

        assert result.benefit_cost_ratio == pytest.approx(0.0)
        assert result.should_intervene is False

    def test_rejects_zero_cost_with_positive_avoided_loss_until_convention_defined(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="benefit_cost_ratio must be finite.",
        ):
            optimize_cost(
                equipment_id="INV-001",
                intervention_cost=0.0,
                failure_probability=1.0,
                failure_cost=1000.0,
            )

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            optimize_cost(
                equipment_id=" ",
                intervention_cost=1000.0,
                failure_probability=0.50,
                failure_cost=5000.0,
            )

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("intervention_cost", math.nan),
            ("failure_probability", math.inf),
            ("failure_cost", -math.inf),
            ("prevention_effectiveness", math.nan),
        ],
    )
    def test_rejects_non_finite_inputs(
        self,
        field_name: str,
        value: float,
    ) -> None:
        inputs = {
            "intervention_cost": 1000.0,
            "failure_probability": 0.50,
            "failure_cost": 5000.0,
            "prevention_effectiveness": 1.0,
        }

        inputs[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            optimize_cost(
                equipment_id="INV-001",
                **inputs,
            )

    def test_rejects_negative_intervention_cost(self) -> None:
        with pytest.raises(
            ValueError,
            match="intervention_cost must not be negative.",
        ):
            optimize_cost(
                equipment_id="INV-001",
                intervention_cost=-1.0,
                failure_probability=0.50,
                failure_cost=5000.0,
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
            optimize_cost(
                equipment_id="INV-001",
                intervention_cost=1000.0,
                failure_probability=failure_probability,
                failure_cost=5000.0,
            )

    def test_rejects_negative_failure_cost(self) -> None:
        with pytest.raises(
            ValueError,
            match="failure_cost must not be negative.",
        ):
            optimize_cost(
                equipment_id="INV-001",
                intervention_cost=1000.0,
                failure_probability=0.50,
                failure_cost=-1.0,
            )

    @pytest.mark.parametrize(
        "effectiveness",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_prevention_effectiveness(
        self,
        effectiveness: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=("prevention_effectiveness must be between 0 and 1."),
        ):
            optimize_cost(
                equipment_id="INV-001",
                intervention_cost=1000.0,
                failure_probability=0.50,
                failure_cost=5000.0,
                prevention_effectiveness=effectiveness,
            )


class TestOptimizeCosts:
    """Tests for batch cost optimization."""

    def test_adds_optimization_columns(self) -> None:
        result = optimize_costs(
            frame=_frame(),
            prevention_effectiveness_column=("prevention_effectiveness"),
        )

        assert "expected_loss_avoided" in result.columns
        assert "net_benefit" in result.columns
        assert "benefit_cost_ratio" in result.columns
        assert "should_intervene" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _frame()

        result = optimize_costs(
            frame=frame,
            prevention_effectiveness_column=("prevention_effectiveness"),
        )

        assert len(result) == len(frame)

    def test_uses_default_effectiveness_when_column_absent(
        self,
    ) -> None:
        frame = _frame().drop(columns=["prevention_effectiveness"])

        result = optimize_costs(frame=frame)

        expected_first_loss = 0.80 * 5000.0

        assert result.loc[
            0,
            "expected_loss_avoided",
        ] == pytest.approx(expected_first_loss)

    def test_uses_custom_effectiveness_column(self) -> None:
        result = optimize_costs(
            frame=_frame(),
            prevention_effectiveness_column=("prevention_effectiveness"),
        )

        assert result.loc[
            2,
            "expected_loss_avoided",
        ] == pytest.approx(0.60 * 4000.0 * 0.50)

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        optimize_costs(
            frame=frame,
            prevention_effectiveness_column=("prevention_effectiveness"),
        )

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Cost optimization frame must not be empty.",
        ):
            optimize_costs(frame=pd.DataFrame())

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["failure_cost"])

        with pytest.raises(
            ValueError,
            match=("Cost optimization frame is missing required columns"),
        ):
            optimize_costs(frame=frame)

    def test_rejects_missing_effectiveness_column_when_requested(
        self,
    ) -> None:
        frame = _frame().drop(columns=["prevention_effectiveness"])

        with pytest.raises(
            ValueError,
            match=("Cost optimization frame is missing required columns"),
        ):
            optimize_costs(
                frame=frame,
                prevention_effectiveness_column=("missing_effectiveness"),
            )

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "equipment_id": "asset_id",
                "intervention_cost": "maintenance_cost",
                "failure_probability": "failure_risk",
                "failure_cost": "expected_failure_cost",
                "prevention_effectiveness": "effectiveness",
            }
        )

        result = optimize_costs(
            frame=frame,
            equipment_id_column="asset_id",
            intervention_cost_column="maintenance_cost",
            failure_probability_column="failure_risk",
            failure_cost_column="expected_failure_cost",
            prevention_effectiveness_column="effectiveness",
        )

        assert "expected_loss_avoided" in result.columns
        assert "net_benefit" in result.columns
        assert "benefit_cost_ratio" in result.columns
        assert "should_intervene" in result.columns
