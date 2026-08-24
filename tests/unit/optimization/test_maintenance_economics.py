"""Unit tests for EOIP maintenance cost-benefit analysis."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.optimization.maintenance_economics import (
    MaintenanceCostBenefitResult,
    analyze_maintenance_cost_benefits,
    evaluate_maintenance_cost_benefit,
)


def _frame() -> pd.DataFrame:
    """Return deterministic maintenance cost-benefit inputs."""
    return pd.DataFrame(
        {
            "equipment_id": [
                "INV-001",
                "INV-002",
                "INV-003",
            ],
            "maintenance_cost": [
                3000.0,
                5000.0,
                1000.0,
            ],
            "failure_probability": [
                0.70,
                0.20,
                0.90,
            ],
            "failure_cost": [
                20000.0,
                10000.0,
                5000.0,
            ],
            "prevention_effectiveness": [
                0.80,
                0.50,
                1.00,
            ],
        }
    )


class TestMaintenanceCostBenefitResult:
    """Tests for maintenance economics result validation."""

    def test_accepts_valid_result(self) -> None:
        result = MaintenanceCostBenefitResult(
            equipment_id="INV-001",
            maintenance_cost=3000.0,
            failure_probability=0.70,
            failure_cost=20000.0,
            prevention_effectiveness=0.80,
            expected_failure_cost=14000.0,
            expected_avoided_cost=11200.0,
            net_benefit=8200.0,
            roi_percentage=273.3333333333,
            economically_justified=True,
        )

        assert result.equipment_id == "INV-001"
        assert result.net_benefit == pytest.approx(8200.0)
        assert result.economically_justified is True

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            MaintenanceCostBenefitResult(
                equipment_id=" ",
                maintenance_cost=1000.0,
                failure_probability=0.50,
                failure_cost=5000.0,
                prevention_effectiveness=1.0,
                expected_failure_cost=2500.0,
                expected_avoided_cost=2500.0,
                net_benefit=1500.0,
                roi_percentage=150.0,
                economically_justified=True,
            )

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("maintenance_cost", math.nan),
            ("failure_probability", math.inf),
            ("failure_cost", -math.inf),
            ("prevention_effectiveness", math.nan),
            ("expected_failure_cost", math.inf),
            ("expected_avoided_cost", -math.inf),
            ("net_benefit", math.nan),
            ("roi_percentage", math.inf),
        ],
    )
    def test_rejects_non_finite_values(
        self,
        field_name: str,
        value: float,
    ) -> None:
        values = {
            "maintenance_cost": 1000.0,
            "failure_probability": 0.50,
            "failure_cost": 5000.0,
            "prevention_effectiveness": 1.0,
            "expected_failure_cost": 2500.0,
            "expected_avoided_cost": 2500.0,
            "net_benefit": 1500.0,
            "roi_percentage": 150.0,
        }

        values[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            MaintenanceCostBenefitResult(
                equipment_id="INV-001",
                economically_justified=True,
                **values,
            )

    def test_rejects_negative_maintenance_cost(self) -> None:
        with pytest.raises(
            ValueError,
            match="maintenance_cost must not be negative.",
        ):
            MaintenanceCostBenefitResult(
                equipment_id="INV-001",
                maintenance_cost=-1.0,
                failure_probability=0.50,
                failure_cost=5000.0,
                prevention_effectiveness=1.0,
                expected_failure_cost=2500.0,
                expected_avoided_cost=2500.0,
                net_benefit=2501.0,
                roi_percentage=0.0,
                economically_justified=True,
            )

    @pytest.mark.parametrize(
        "value",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_failure_probability(
        self,
        value: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="failure_probability must be between 0 and 1.",
        ):
            MaintenanceCostBenefitResult(
                equipment_id="INV-001",
                maintenance_cost=1000.0,
                failure_probability=value,
                failure_cost=5000.0,
                prevention_effectiveness=1.0,
                expected_failure_cost=2500.0,
                expected_avoided_cost=2500.0,
                net_benefit=1500.0,
                roi_percentage=150.0,
                economically_justified=True,
            )

    @pytest.mark.parametrize(
        "value",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_prevention_effectiveness(
        self,
        value: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="prevention_effectiveness must be between 0 and 1.",
        ):
            MaintenanceCostBenefitResult(
                equipment_id="INV-001",
                maintenance_cost=1000.0,
                failure_probability=0.50,
                failure_cost=5000.0,
                prevention_effectiveness=value,
                expected_failure_cost=2500.0,
                expected_avoided_cost=2500.0,
                net_benefit=1500.0,
                roi_percentage=150.0,
                economically_justified=True,
            )


class TestEvaluateMaintenanceCostBenefit:
    """Tests for individual maintenance economics."""

    def test_calculates_expected_failure_cost(self) -> None:
        result = evaluate_maintenance_cost_benefit(
            equipment_id="INV-001",
            maintenance_cost=3000.0,
            failure_probability=0.70,
            failure_cost=20000.0,
            prevention_effectiveness=0.80,
        )

        assert result.expected_failure_cost == pytest.approx(14000.0)

    def test_calculates_expected_avoided_cost(self) -> None:
        result = evaluate_maintenance_cost_benefit(
            equipment_id="INV-001",
            maintenance_cost=3000.0,
            failure_probability=0.70,
            failure_cost=20000.0,
            prevention_effectiveness=0.80,
        )

        assert result.expected_avoided_cost == pytest.approx(11200.0)

    def test_calculates_net_benefit(self) -> None:
        result = evaluate_maintenance_cost_benefit(
            equipment_id="INV-001",
            maintenance_cost=3000.0,
            failure_probability=0.70,
            failure_cost=20000.0,
            prevention_effectiveness=0.80,
        )

        assert result.net_benefit == pytest.approx(8200.0)

    def test_calculates_roi(self) -> None:
        result = evaluate_maintenance_cost_benefit(
            equipment_id="INV-001",
            maintenance_cost=3000.0,
            failure_probability=0.70,
            failure_cost=20000.0,
            prevention_effectiveness=0.80,
        )

        assert result.roi_percentage == pytest.approx(8200.0 / 3000.0 * 100.0)

    def test_positive_net_benefit_is_justified(self) -> None:
        result = evaluate_maintenance_cost_benefit(
            equipment_id="INV-001",
            maintenance_cost=1000.0,
            failure_probability=0.80,
            failure_cost=5000.0,
        )

        assert result.economically_justified is True

    def test_negative_net_benefit_is_not_justified(self) -> None:
        result = evaluate_maintenance_cost_benefit(
            equipment_id="INV-001",
            maintenance_cost=5000.0,
            failure_probability=0.20,
            failure_cost=10000.0,
        )

        assert result.net_benefit == pytest.approx(-3000.0)
        assert result.economically_justified is False

    def test_break_even_is_not_justified(self) -> None:
        result = evaluate_maintenance_cost_benefit(
            equipment_id="INV-001",
            maintenance_cost=1000.0,
            failure_probability=0.50,
            failure_cost=2000.0,
        )

        assert result.net_benefit == pytest.approx(0.0)
        assert result.economically_justified is False

    def test_zero_maintenance_cost_uses_finite_roi_convention(
        self,
    ) -> None:
        result = evaluate_maintenance_cost_benefit(
            equipment_id="INV-001",
            maintenance_cost=0.0,
            failure_probability=1.0,
            failure_cost=1000.0,
        )

        assert result.expected_avoided_cost == pytest.approx(1000.0)
        assert result.net_benefit == pytest.approx(1000.0)
        assert result.roi_percentage == pytest.approx(0.0)
        assert result.economically_justified is True

    def test_zero_effectiveness_avoids_nothing(self) -> None:
        result = evaluate_maintenance_cost_benefit(
            equipment_id="INV-001",
            maintenance_cost=1000.0,
            failure_probability=1.0,
            failure_cost=10000.0,
            prevention_effectiveness=0.0,
        )

        assert result.expected_avoided_cost == pytest.approx(0.0)
        assert result.net_benefit == pytest.approx(-1000.0)

    def test_rejects_empty_equipment_id(self) -> None:
        with pytest.raises(
            ValueError,
            match="equipment_id must not be empty.",
        ):
            evaluate_maintenance_cost_benefit(
                equipment_id=" ",
                maintenance_cost=1000.0,
                failure_probability=0.50,
                failure_cost=5000.0,
            )

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("maintenance_cost", math.nan),
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
            "maintenance_cost": 1000.0,
            "failure_probability": 0.50,
            "failure_cost": 5000.0,
            "prevention_effectiveness": 1.0,
        }

        inputs[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            evaluate_maintenance_cost_benefit(
                equipment_id="INV-001",
                **inputs,
            )


class TestAnalyzeMaintenanceCostBenefits:
    """Tests for batch maintenance cost-benefit analysis."""

    def test_adds_economic_columns(self) -> None:
        result = analyze_maintenance_cost_benefits(
            frame=_frame(),
            prevention_effectiveness_column=("prevention_effectiveness"),
        )

        assert "expected_failure_cost" in result.columns
        assert "expected_avoided_cost" in result.columns
        assert "net_benefit" in result.columns
        assert "roi_percentage" in result.columns
        assert "economically_justified" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _frame()

        result = analyze_maintenance_cost_benefits(
            frame=frame,
            prevention_effectiveness_column=("prevention_effectiveness"),
        )

        assert len(result) == len(frame)

    def test_calculates_first_row_correctly(self) -> None:
        result = analyze_maintenance_cost_benefits(
            frame=_frame(),
            prevention_effectiveness_column=("prevention_effectiveness"),
        )

        assert result.loc[
            0,
            "expected_failure_cost",
        ] == pytest.approx(14000.0)

        assert result.loc[
            0,
            "expected_avoided_cost",
        ] == pytest.approx(11200.0)

        assert result.loc[
            0,
            "net_benefit",
        ] == pytest.approx(8200.0)

    def test_uses_default_effectiveness_when_not_supplied(
        self,
    ) -> None:
        frame = _frame().drop(columns=["prevention_effectiveness"])

        result = analyze_maintenance_cost_benefits(frame=frame)

        assert result.loc[
            0,
            "expected_avoided_cost",
        ] == pytest.approx(0.70 * 20000.0)

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        analyze_maintenance_cost_benefits(
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
            match=("Maintenance cost-benefit frame must not be empty."),
        ):
            analyze_maintenance_cost_benefits(frame=pd.DataFrame())

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["failure_cost"])

        with pytest.raises(
            ValueError,
            match=("Maintenance cost-benefit frame is missing " "required columns"),
        ):
            analyze_maintenance_cost_benefits(frame=frame)

    def test_rejects_non_numeric_column(self) -> None:
        frame = _frame()
        frame["maintenance_cost"] = [
            "a",
            "b",
            "c",
        ]

        with pytest.raises(
            TypeError,
            match="Column 'maintenance_cost' must be numeric.",
        ):
            analyze_maintenance_cost_benefits(frame=frame)

    def test_rejects_missing_numeric_value(self) -> None:
        frame = _frame()
        frame.loc[
            0,
            "failure_probability",
        ] = math.nan

        with pytest.raises(
            ValueError,
            match=("Column 'failure_probability' must not contain " "missing values."),
        ):
            analyze_maintenance_cost_benefits(frame=frame)

    def test_rejects_non_finite_numeric_value(self) -> None:
        frame = _frame()
        frame.loc[
            0,
            "failure_cost",
        ] = math.inf

        with pytest.raises(
            ValueError,
            match=("Column 'failure_cost' must contain only " "finite values."),
        ):
            analyze_maintenance_cost_benefits(frame=frame)

    def test_rejects_blank_equipment_identifier(self) -> None:
        frame = _frame()
        frame.loc[
            0,
            "equipment_id",
        ] = " "

        with pytest.raises(
            ValueError,
            match="Equipment identifiers must not be empty.",
        ):
            analyze_maintenance_cost_benefits(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "equipment_id": "asset_id",
                "maintenance_cost": "service_cost",
                "failure_probability": "failure_risk",
                "failure_cost": "consequence_cost",
                "prevention_effectiveness": "effectiveness",
            }
        )

        result = analyze_maintenance_cost_benefits(
            frame=frame,
            equipment_id_column="asset_id",
            maintenance_cost_column="service_cost",
            failure_probability_column="failure_risk",
            failure_cost_column="consequence_cost",
            prevention_effectiveness_column="effectiveness",
        )

        assert "expected_failure_cost" in result.columns
        assert "expected_avoided_cost" in result.columns
        assert "net_benefit" in result.columns
        assert "roi_percentage" in result.columns
        assert "economically_justified" in result.columns
