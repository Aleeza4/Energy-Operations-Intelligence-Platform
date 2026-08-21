"""Unit tests for EOIP optimization validation."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.optimization.validation import (
    OptimizationValidationResult,
    validate_optimization_outputs,
)


def _frame() -> pd.DataFrame:
    """Return deterministic optimization-validation inputs."""
    return pd.DataFrame(
        {
            "recoverable_energy_kwh": [
                500.0,
                250.0,
                0.0,
                100.0,
            ],
            "net_financial_impact": [
                3000.0,
                -500.0,
                0.0,
                1000.0,
            ],
            "recommendation_type": [
                "maintenance",
                "performance_recovery",
                "no_action",
                "monitor",
            ],
            "economically_justified": [
                True,
                False,
                False,
                True,
            ],
        }
    )


class TestOptimizationValidationResult:
    """Tests for optimization validation summary."""

    def test_accepts_valid_result(self) -> None:
        result = OptimizationValidationResult(
            row_count=4,
            recommendation_count=3,
            positive_net_impact_count=2,
            negative_net_impact_count=1,
            zero_net_impact_count=1,
            intervention_count=2,
            total_recoverable_energy_kwh=850.0,
            total_net_financial_impact=3500.0,
            validation_passed=True,
        )

        assert result.row_count == 4
        assert result.recommendation_count == 3
        assert result.intervention_count == 2
        assert result.validation_passed is True

    @pytest.mark.parametrize(
        "field_name",
        [
            "row_count",
            "recommendation_count",
            "positive_net_impact_count",
            "negative_net_impact_count",
            "zero_net_impact_count",
            "intervention_count",
        ],
    )
    def test_rejects_negative_counts(
        self,
        field_name: str,
    ) -> None:
        values = {
            "row_count": 4,
            "recommendation_count": 3,
            "positive_net_impact_count": 2,
            "negative_net_impact_count": 1,
            "zero_net_impact_count": 1,
            "intervention_count": 2,
        }

        values[field_name] = -1

        with pytest.raises(
            ValueError,
            match=f"{field_name} must not be negative.",
        ):
            OptimizationValidationResult(
                **values,
                total_recoverable_energy_kwh=850.0,
                total_net_financial_impact=3500.0,
                validation_passed=True,
            )

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("total_recoverable_energy_kwh", math.nan),
            ("total_recoverable_energy_kwh", math.inf),
            ("total_net_financial_impact", math.nan),
            ("total_net_financial_impact", -math.inf),
        ],
    )
    def test_rejects_non_finite_totals(
        self,
        field_name: str,
        value: float,
    ) -> None:
        totals = {
            "total_recoverable_energy_kwh": 850.0,
            "total_net_financial_impact": 3500.0,
        }

        totals[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            OptimizationValidationResult(
                row_count=4,
                recommendation_count=3,
                positive_net_impact_count=2,
                negative_net_impact_count=1,
                zero_net_impact_count=1,
                intervention_count=2,
                validation_passed=True,
                **totals,
            )

    def test_rejects_negative_total_recoverable_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match=("total_recoverable_energy_kwh must not be negative."),
        ):
            OptimizationValidationResult(
                row_count=4,
                recommendation_count=3,
                positive_net_impact_count=2,
                negative_net_impact_count=1,
                zero_net_impact_count=1,
                intervention_count=2,
                total_recoverable_energy_kwh=-1.0,
                total_net_financial_impact=3500.0,
                validation_passed=True,
            )

    def test_allows_negative_total_financial_impact(self) -> None:
        result = OptimizationValidationResult(
            row_count=2,
            recommendation_count=1,
            positive_net_impact_count=0,
            negative_net_impact_count=2,
            zero_net_impact_count=0,
            intervention_count=0,
            total_recoverable_energy_kwh=100.0,
            total_net_financial_impact=-5000.0,
            validation_passed=True,
        )

        assert result.total_net_financial_impact == pytest.approx(-5000.0)

    def test_rejects_financial_impact_count_mismatch(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Financial-impact counts must equal row_count."),
        ):
            OptimizationValidationResult(
                row_count=4,
                recommendation_count=3,
                positive_net_impact_count=1,
                negative_net_impact_count=1,
                zero_net_impact_count=1,
                intervention_count=2,
                total_recoverable_energy_kwh=850.0,
                total_net_financial_impact=3500.0,
                validation_passed=True,
            )

    def test_rejects_recommendation_count_above_row_count(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=("recommendation_count must not exceed row_count."),
        ):
            OptimizationValidationResult(
                row_count=4,
                recommendation_count=5,
                positive_net_impact_count=2,
                negative_net_impact_count=1,
                zero_net_impact_count=1,
                intervention_count=2,
                total_recoverable_energy_kwh=850.0,
                total_net_financial_impact=3500.0,
                validation_passed=True,
            )

    def test_rejects_intervention_count_above_row_count(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=("intervention_count must not exceed row_count."),
        ):
            OptimizationValidationResult(
                row_count=4,
                recommendation_count=3,
                positive_net_impact_count=2,
                negative_net_impact_count=1,
                zero_net_impact_count=1,
                intervention_count=5,
                total_recoverable_energy_kwh=850.0,
                total_net_financial_impact=3500.0,
                validation_passed=True,
            )


class TestValidateOptimizationOutputs:
    """Tests for portfolio optimization validation."""

    def test_returns_expected_summary(self) -> None:
        result = validate_optimization_outputs(frame=_frame())

        assert result.row_count == 4
        assert result.recommendation_count == 3
        assert result.positive_net_impact_count == 2
        assert result.negative_net_impact_count == 1
        assert result.zero_net_impact_count == 1
        assert result.intervention_count == 2

    def test_calculates_total_recoverable_energy(self) -> None:
        result = validate_optimization_outputs(frame=_frame())

        assert result.total_recoverable_energy_kwh == pytest.approx(850.0)

    def test_calculates_total_net_financial_impact(self) -> None:
        result = validate_optimization_outputs(frame=_frame())

        assert result.total_net_financial_impact == pytest.approx(3500.0)

    def test_validation_passes_for_valid_frame(self) -> None:
        result = validate_optimization_outputs(frame=_frame())

        assert result.validation_passed is True

    def test_no_action_is_not_counted_as_recommendation(self) -> None:
        frame = pd.DataFrame(
            {
                "recoverable_energy_kwh": [0.0],
                "net_financial_impact": [0.0],
                "recommendation_type": ["no_action"],
                "economically_justified": [False],
            }
        )

        result = validate_optimization_outputs(frame=frame)

        assert result.recommendation_count == 0

    def test_all_action_types_except_no_action_are_counted(
        self,
    ) -> None:
        frame = pd.DataFrame(
            {
                "recoverable_energy_kwh": [
                    100.0,
                    100.0,
                    100.0,
                ],
                "net_financial_impact": [
                    100.0,
                    100.0,
                    100.0,
                ],
                "recommendation_type": [
                    "maintenance",
                    "performance_recovery",
                    "monitor",
                ],
                "economically_justified": [
                    True,
                    False,
                    False,
                ],
            }
        )

        result = validate_optimization_outputs(frame=frame)

        assert result.recommendation_count == 3

    def test_counts_positive_negative_and_zero_impacts(
        self,
    ) -> None:
        frame = pd.DataFrame(
            {
                "recoverable_energy_kwh": [
                    100.0,
                    100.0,
                    100.0,
                ],
                "net_financial_impact": [
                    1.0,
                    -1.0,
                    0.0,
                ],
                "recommendation_type": [
                    "maintenance",
                    "monitor",
                    "no_action",
                ],
                "economically_justified": [
                    True,
                    False,
                    False,
                ],
            }
        )

        result = validate_optimization_outputs(frame=frame)

        assert result.positive_net_impact_count == 1
        assert result.negative_net_impact_count == 1
        assert result.zero_net_impact_count == 1

    def test_counts_intervention_flags(self) -> None:
        frame = pd.DataFrame(
            {
                "recoverable_energy_kwh": [
                    100.0,
                    0.0,
                    50.0,
                ],
                "net_financial_impact": [
                    1000.0,
                    -500.0,
                    200.0,
                ],
                "recommendation_type": [
                    "maintenance",
                    "no_action",
                    "performance_recovery",
                ],
                "economically_justified": [
                    True,
                    False,
                    True,
                ],
            }
        )

        result = validate_optimization_outputs(frame=frame)

        assert result.intervention_count == 2

    def test_allows_negative_portfolio_financial_impact(
        self,
    ) -> None:
        frame = pd.DataFrame(
            {
                "recoverable_energy_kwh": [
                    100.0,
                    50.0,
                ],
                "net_financial_impact": [
                    -1000.0,
                    -2000.0,
                ],
                "recommendation_type": [
                    "monitor",
                    "no_action",
                ],
                "economically_justified": [
                    False,
                    False,
                ],
            }
        )

        result = validate_optimization_outputs(frame=frame)

        assert result.total_net_financial_impact == pytest.approx(-3000.0)

        assert result.validation_passed is True

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Optimization validation frame must not be empty."),
        ):
            validate_optimization_outputs(frame=pd.DataFrame())

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["recommendation_type"])

        with pytest.raises(
            ValueError,
            match=("Optimization validation frame is missing " "required columns"),
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_non_numeric_recoverable_energy(self) -> None:
        frame = _frame()

        frame["recoverable_energy_kwh"] = [
            "a",
            "b",
            "c",
            "d",
        ]

        with pytest.raises(
            TypeError,
            match=("Recoverable energy column must be numeric."),
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_non_numeric_net_financial_impact(
        self,
    ) -> None:
        frame = _frame()

        frame["net_financial_impact"] = [
            "a",
            "b",
            "c",
            "d",
        ]

        with pytest.raises(
            TypeError,
            match=("Net financial impact column must be numeric."),
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_missing_recoverable_energy(self) -> None:
        frame = _frame()
        frame.loc[
            0,
            "recoverable_energy_kwh",
        ] = math.nan

        with pytest.raises(
            ValueError,
            match=("Recoverable energy column must not contain " "missing values."),
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_missing_net_financial_impact(self) -> None:
        frame = _frame()
        frame.loc[
            0,
            "net_financial_impact",
        ] = math.nan

        with pytest.raises(
            ValueError,
            match=("Net financial impact column must not contain " "missing values."),
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_non_finite_recoverable_energy(self) -> None:
        frame = _frame()
        frame.loc[
            0,
            "recoverable_energy_kwh",
        ] = math.inf

        with pytest.raises(
            ValueError,
            match=("Recoverable energy values must contain only " "finite values."),
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_non_finite_net_financial_impact(
        self,
    ) -> None:
        frame = _frame()
        frame.loc[
            0,
            "net_financial_impact",
        ] = math.inf

        with pytest.raises(
            ValueError,
            match=("Net financial impact values must contain only " "finite values."),
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_negative_recoverable_energy(self) -> None:
        frame = _frame()
        frame.loc[
            0,
            "recoverable_energy_kwh",
        ] = -1.0

        with pytest.raises(
            ValueError,
            match=("Recoverable energy values must not be negative."),
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_missing_recommendation_type(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "recommendation_type",
        ] = None

        with pytest.raises(
            ValueError,
            match=("Recommendation type column must not contain " "missing values."),
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_blank_recommendation_type(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "recommendation_type",
        ] = " "

        with pytest.raises(
            ValueError,
            match="Recommendation types must not be empty.",
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_unsupported_recommendation_type(
        self,
    ) -> None:
        frame = _frame()

        frame.loc[
            0,
            "recommendation_type",
        ] = "unknown"

        with pytest.raises(
            ValueError,
            match="Unsupported recommendation types",
        ):
            validate_optimization_outputs(frame=frame)

    def test_rejects_missing_intervention_value(self) -> None:
        frame = _frame()

        frame["economically_justified"] = frame["economically_justified"].astype(
            "boolean"
        )

        frame.loc[
            0,
            "economically_justified",
        ] = pd.NA

        with pytest.raises(
            ValueError,
            match=("Intervention column must not contain missing values."),
        ):
            validate_optimization_outputs(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "recoverable_energy_kwh": "recoverable",
                "net_financial_impact": "net_value",
                "recommendation_type": "action_type",
                "economically_justified": "intervene",
            }
        )

        result = validate_optimization_outputs(
            frame=frame,
            recoverable_energy_column="recoverable",
            net_financial_impact_column="net_value",
            recommendation_type_column="action_type",
            intervention_column="intervene",
        )

        assert result.row_count == 4
        assert result.validation_passed is True
