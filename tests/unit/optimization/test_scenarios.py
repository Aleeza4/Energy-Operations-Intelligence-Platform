"""Unit tests for EOIP optimization scenario analysis."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.optimization.scenarios import (
    ScenarioComparisonResult,
    analyze_scenarios,
    compare_scenarios,
)


def _frame() -> pd.DataFrame:
    """Return deterministic scenario-analysis inputs."""
    return pd.DataFrame(
        {
            "baseline_energy_kwh": [
                1000.0,
                2000.0,
                1500.0,
            ],
            "intervention_energy_kwh": [
                1200.0,
                1900.0,
                1500.0,
            ],
            "baseline_cost": [
                10000.0,
                8000.0,
                5000.0,
            ],
            "intervention_cost": [
                7000.0,
                9000.0,
                5000.0,
            ],
            "baseline_risk": [
                0.80,
                0.40,
                0.20,
            ],
            "intervention_risk": [
                0.30,
                0.50,
                0.20,
            ],
        }
    )


class TestScenarioComparisonResult:
    """Tests for scenario-comparison result validation."""

    def test_accepts_valid_result(self) -> None:
        result = ScenarioComparisonResult(
            baseline_energy_kwh=1000.0,
            intervention_energy_kwh=1200.0,
            baseline_cost=10000.0,
            intervention_cost=7000.0,
            baseline_risk=0.80,
            intervention_risk=0.30,
            energy_gain_kwh=200.0,
            cost_saving=3000.0,
            risk_reduction=0.50,
        )

        assert result.energy_gain_kwh == pytest.approx(200.0)
        assert result.cost_saving == pytest.approx(3000.0)
        assert result.risk_reduction == pytest.approx(0.50)

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("baseline_energy_kwh", math.nan),
            ("intervention_energy_kwh", math.inf),
            ("baseline_cost", -math.inf),
            ("intervention_cost", math.nan),
            ("baseline_risk", math.inf),
            ("intervention_risk", -math.inf),
            ("energy_gain_kwh", math.nan),
            ("cost_saving", math.inf),
            ("risk_reduction", -math.inf),
        ],
    )
    def test_rejects_non_finite_values(
        self,
        field_name: str,
        value: float,
    ) -> None:
        values = {
            "baseline_energy_kwh": 1000.0,
            "intervention_energy_kwh": 1200.0,
            "baseline_cost": 10000.0,
            "intervention_cost": 7000.0,
            "baseline_risk": 0.80,
            "intervention_risk": 0.30,
            "energy_gain_kwh": 200.0,
            "cost_saving": 3000.0,
            "risk_reduction": 0.50,
        }

        values[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            ScenarioComparisonResult(**values)

    def test_rejects_negative_baseline_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match="baseline_energy_kwh must not be negative.",
        ):
            ScenarioComparisonResult(
                baseline_energy_kwh=-1.0,
                intervention_energy_kwh=1000.0,
                baseline_cost=1000.0,
                intervention_cost=900.0,
                baseline_risk=0.50,
                intervention_risk=0.40,
                energy_gain_kwh=1001.0,
                cost_saving=100.0,
                risk_reduction=0.10,
            )

    def test_rejects_negative_intervention_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match="intervention_energy_kwh must not be negative.",
        ):
            ScenarioComparisonResult(
                baseline_energy_kwh=1000.0,
                intervention_energy_kwh=-1.0,
                baseline_cost=1000.0,
                intervention_cost=900.0,
                baseline_risk=0.50,
                intervention_risk=0.40,
                energy_gain_kwh=-1001.0,
                cost_saving=100.0,
                risk_reduction=0.10,
            )

    def test_rejects_negative_baseline_cost(self) -> None:
        with pytest.raises(
            ValueError,
            match="baseline_cost must not be negative.",
        ):
            ScenarioComparisonResult(
                baseline_energy_kwh=1000.0,
                intervention_energy_kwh=1100.0,
                baseline_cost=-1.0,
                intervention_cost=900.0,
                baseline_risk=0.50,
                intervention_risk=0.40,
                energy_gain_kwh=100.0,
                cost_saving=-901.0,
                risk_reduction=0.10,
            )

    def test_rejects_negative_intervention_cost(self) -> None:
        with pytest.raises(
            ValueError,
            match="intervention_cost must not be negative.",
        ):
            ScenarioComparisonResult(
                baseline_energy_kwh=1000.0,
                intervention_energy_kwh=1100.0,
                baseline_cost=1000.0,
                intervention_cost=-1.0,
                baseline_risk=0.50,
                intervention_risk=0.40,
                energy_gain_kwh=100.0,
                cost_saving=1001.0,
                risk_reduction=0.10,
            )

    @pytest.mark.parametrize(
        "risk",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_baseline_risk(
        self,
        risk: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="baseline_risk must be between 0 and 1.",
        ):
            ScenarioComparisonResult(
                baseline_energy_kwh=1000.0,
                intervention_energy_kwh=1100.0,
                baseline_cost=1000.0,
                intervention_cost=900.0,
                baseline_risk=risk,
                intervention_risk=0.40,
                energy_gain_kwh=100.0,
                cost_saving=100.0,
                risk_reduction=0.10,
            )

    @pytest.mark.parametrize(
        "risk",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_intervention_risk(
        self,
        risk: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="intervention_risk must be between 0 and 1.",
        ):
            ScenarioComparisonResult(
                baseline_energy_kwh=1000.0,
                intervention_energy_kwh=1100.0,
                baseline_cost=1000.0,
                intervention_cost=900.0,
                baseline_risk=0.50,
                intervention_risk=risk,
                energy_gain_kwh=100.0,
                cost_saving=100.0,
                risk_reduction=0.10,
            )


class TestCompareScenarios:
    """Tests for individual scenario comparisons."""

    def test_calculates_energy_gain(self) -> None:
        result = compare_scenarios(
            baseline_energy_kwh=1000.0,
            intervention_energy_kwh=1250.0,
            baseline_cost=10000.0,
            intervention_cost=7000.0,
            baseline_risk=0.80,
            intervention_risk=0.30,
        )

        assert result.energy_gain_kwh == pytest.approx(250.0)

    def test_calculates_cost_saving(self) -> None:
        result = compare_scenarios(
            baseline_energy_kwh=1000.0,
            intervention_energy_kwh=1250.0,
            baseline_cost=10000.0,
            intervention_cost=7000.0,
            baseline_risk=0.80,
            intervention_risk=0.30,
        )

        assert result.cost_saving == pytest.approx(3000.0)

    def test_calculates_risk_reduction(self) -> None:
        result = compare_scenarios(
            baseline_energy_kwh=1000.0,
            intervention_energy_kwh=1250.0,
            baseline_cost=10000.0,
            intervention_cost=7000.0,
            baseline_risk=0.80,
            intervention_risk=0.30,
        )

        assert result.risk_reduction == pytest.approx(0.50)

    def test_allows_negative_energy_gain(self) -> None:
        result = compare_scenarios(
            baseline_energy_kwh=1000.0,
            intervention_energy_kwh=900.0,
            baseline_cost=10000.0,
            intervention_cost=7000.0,
            baseline_risk=0.80,
            intervention_risk=0.30,
        )

        assert result.energy_gain_kwh == pytest.approx(-100.0)

    def test_allows_negative_cost_saving(self) -> None:
        result = compare_scenarios(
            baseline_energy_kwh=1000.0,
            intervention_energy_kwh=1100.0,
            baseline_cost=7000.0,
            intervention_cost=9000.0,
            baseline_risk=0.80,
            intervention_risk=0.30,
        )

        assert result.cost_saving == pytest.approx(-2000.0)

    def test_allows_negative_risk_reduction(self) -> None:
        result = compare_scenarios(
            baseline_energy_kwh=1000.0,
            intervention_energy_kwh=1100.0,
            baseline_cost=7000.0,
            intervention_cost=6000.0,
            baseline_risk=0.30,
            intervention_risk=0.60,
        )

        assert result.risk_reduction == pytest.approx(-0.30)

    def test_identical_scenarios_have_zero_change(self) -> None:
        result = compare_scenarios(
            baseline_energy_kwh=1000.0,
            intervention_energy_kwh=1000.0,
            baseline_cost=5000.0,
            intervention_cost=5000.0,
            baseline_risk=0.50,
            intervention_risk=0.50,
        )

        assert result.energy_gain_kwh == pytest.approx(0.0)
        assert result.cost_saving == pytest.approx(0.0)
        assert result.risk_reduction == pytest.approx(0.0)

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("baseline_energy_kwh", math.nan),
            ("intervention_energy_kwh", math.inf),
            ("baseline_cost", -math.inf),
            ("intervention_cost", math.nan),
            ("baseline_risk", math.inf),
            ("intervention_risk", -math.inf),
        ],
    )
    def test_rejects_non_finite_inputs(
        self,
        field_name: str,
        value: float,
    ) -> None:
        inputs = {
            "baseline_energy_kwh": 1000.0,
            "intervention_energy_kwh": 1200.0,
            "baseline_cost": 10000.0,
            "intervention_cost": 7000.0,
            "baseline_risk": 0.80,
            "intervention_risk": 0.30,
        }

        inputs[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            compare_scenarios(**inputs)


class TestAnalyzeScenarios:
    """Tests for batch scenario analysis."""

    def test_adds_analysis_columns(self) -> None:
        result = analyze_scenarios(frame=_frame())

        assert "energy_gain_kwh" in result.columns
        assert "cost_saving" in result.columns
        assert "risk_reduction" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _frame()

        result = analyze_scenarios(frame=frame)

        assert len(result) == len(frame)

    def test_calculates_expected_energy_gains(self) -> None:
        result = analyze_scenarios(frame=_frame())

        assert result["energy_gain_kwh"].tolist() == pytest.approx(
            [
                200.0,
                -100.0,
                0.0,
            ]
        )

    def test_calculates_expected_cost_savings(self) -> None:
        result = analyze_scenarios(frame=_frame())

        assert result["cost_saving"].tolist() == pytest.approx(
            [
                3000.0,
                -1000.0,
                0.0,
            ]
        )

    def test_calculates_expected_risk_reductions(self) -> None:
        result = analyze_scenarios(frame=_frame())

        assert result["risk_reduction"].tolist() == pytest.approx(
            [
                0.50,
                -0.10,
                0.0,
            ]
        )

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        analyze_scenarios(frame=frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Scenario analysis frame must not be empty.",
        ):
            analyze_scenarios(frame=pd.DataFrame())

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["baseline_cost"])

        with pytest.raises(
            ValueError,
            match=("Scenario analysis frame is missing required columns"),
        ):
            analyze_scenarios(frame=frame)

    def test_rejects_non_numeric_column(self) -> None:
        frame = _frame()

        frame["baseline_energy_kwh"] = [
            "a",
            "b",
            "c",
        ]

        with pytest.raises(
            TypeError,
            match=("Column 'baseline_energy_kwh' must be numeric."),
        ):
            analyze_scenarios(frame=frame)

    def test_rejects_missing_numeric_value(self) -> None:
        frame = _frame()
        frame.loc[0, "baseline_cost"] = math.nan

        with pytest.raises(
            ValueError,
            match=("Column 'baseline_cost' must not contain " "missing values."),
        ):
            analyze_scenarios(frame=frame)

    def test_rejects_non_finite_numeric_value(self) -> None:
        frame = _frame()
        frame.loc[
            0,
            "intervention_energy_kwh",
        ] = math.inf

        with pytest.raises(
            ValueError,
            match=(
                "Column 'intervention_energy_kwh' must contain " "only finite values."
            ),
        ):
            analyze_scenarios(frame=frame)

    def test_rejects_negative_energy_through_comparison(
        self,
    ) -> None:
        frame = _frame()
        frame.loc[
            0,
            "baseline_energy_kwh",
        ] = -1.0

        with pytest.raises(
            ValueError,
            match="baseline_energy_kwh must not be negative.",
        ):
            analyze_scenarios(frame=frame)

    def test_rejects_negative_cost_through_comparison(
        self,
    ) -> None:
        frame = _frame()
        frame.loc[
            0,
            "intervention_cost",
        ] = -1.0

        with pytest.raises(
            ValueError,
            match="intervention_cost must not be negative.",
        ):
            analyze_scenarios(frame=frame)

    def test_rejects_invalid_risk_through_comparison(
        self,
    ) -> None:
        frame = _frame()
        frame.loc[
            0,
            "baseline_risk",
        ] = 1.01

        with pytest.raises(
            ValueError,
            match="baseline_risk must be between 0 and 1.",
        ):
            analyze_scenarios(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "baseline_energy_kwh": "energy_before",
                "intervention_energy_kwh": "energy_after",
                "baseline_cost": "cost_before",
                "intervention_cost": "cost_after",
                "baseline_risk": "risk_before",
                "intervention_risk": "risk_after",
            }
        )

        result = analyze_scenarios(
            frame=frame,
            baseline_energy_column="energy_before",
            intervention_energy_column="energy_after",
            baseline_cost_column="cost_before",
            intervention_cost_column="cost_after",
            baseline_risk_column="risk_before",
            intervention_risk_column="risk_after",
        )

        assert "energy_gain_kwh" in result.columns
        assert "cost_saving" in result.columns
        assert "risk_reduction" in result.columns
