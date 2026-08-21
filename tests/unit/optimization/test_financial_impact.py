"""Unit tests for EOIP financial-impact estimation."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.optimization.financial_impact import (
    FinancialImpactResult,
    estimate_financial_impact,
    estimate_financial_impacts,
)


def _frame() -> pd.DataFrame:
    """Return deterministic financial-impact inputs."""
    return pd.DataFrame(
        {
            "recovered_energy_kwh": [
                5000.0,
                1000.0,
                0.0,
            ],
            "energy_value_per_kwh": [
                0.12,
                0.10,
                0.15,
            ],
            "avoided_failure_cost": [
                4000.0,
                500.0,
                0.0,
            ],
            "operating_cost_saving": [
                1000.0,
                200.0,
                0.0,
            ],
            "intervention_cost": [
                2000.0,
                1000.0,
                0.0,
            ],
        }
    )


class TestFinancialImpactResult:
    """Tests for financial-impact result validation."""

    def test_accepts_valid_result(self) -> None:
        result = FinancialImpactResult(
            recovered_energy_kwh=5000.0,
            energy_value_per_kwh=0.12,
            avoided_failure_cost=4000.0,
            operating_cost_saving=1000.0,
            intervention_cost=2000.0,
            recovered_energy_value=600.0,
            gross_financial_benefit=5600.0,
            net_financial_impact=3600.0,
            roi_percentage=180.0,
        )

        assert result.recovered_energy_value == pytest.approx(600.0)
        assert result.gross_financial_benefit == pytest.approx(5600.0)
        assert result.net_financial_impact == pytest.approx(3600.0)
        assert result.roi_percentage == pytest.approx(180.0)

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("recovered_energy_kwh", math.nan),
            ("energy_value_per_kwh", math.inf),
            ("avoided_failure_cost", -math.inf),
            ("operating_cost_saving", math.nan),
            ("intervention_cost", math.inf),
            ("recovered_energy_value", -math.inf),
            ("gross_financial_benefit", math.nan),
            ("net_financial_impact", math.inf),
            ("roi_percentage", -math.inf),
        ],
    )
    def test_rejects_non_finite_values(
        self,
        field_name: str,
        value: float,
    ) -> None:
        values = {
            "recovered_energy_kwh": 5000.0,
            "energy_value_per_kwh": 0.12,
            "avoided_failure_cost": 4000.0,
            "operating_cost_saving": 1000.0,
            "intervention_cost": 2000.0,
            "recovered_energy_value": 600.0,
            "gross_financial_benefit": 5600.0,
            "net_financial_impact": 3600.0,
            "roi_percentage": 180.0,
        }

        values[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            FinancialImpactResult(**values)

    @pytest.mark.parametrize(
        "field_name",
        [
            "recovered_energy_kwh",
            "energy_value_per_kwh",
            "avoided_failure_cost",
            "operating_cost_saving",
            "intervention_cost",
            "recovered_energy_value",
            "gross_financial_benefit",
        ],
    )
    def test_rejects_negative_non_negative_fields(
        self,
        field_name: str,
    ) -> None:
        values = {
            "recovered_energy_kwh": 5000.0,
            "energy_value_per_kwh": 0.12,
            "avoided_failure_cost": 4000.0,
            "operating_cost_saving": 1000.0,
            "intervention_cost": 2000.0,
            "recovered_energy_value": 600.0,
            "gross_financial_benefit": 5600.0,
            "net_financial_impact": 3600.0,
            "roi_percentage": 180.0,
        }

        values[field_name] = -1.0

        with pytest.raises(
            ValueError,
            match=f"{field_name} must not be negative.",
        ):
            FinancialImpactResult(**values)

    def test_allows_negative_net_financial_impact(self) -> None:
        result = FinancialImpactResult(
            recovered_energy_kwh=0.0,
            energy_value_per_kwh=0.12,
            avoided_failure_cost=0.0,
            operating_cost_saving=0.0,
            intervention_cost=1000.0,
            recovered_energy_value=0.0,
            gross_financial_benefit=0.0,
            net_financial_impact=-1000.0,
            roi_percentage=-100.0,
        )

        assert result.net_financial_impact == pytest.approx(-1000.0)
        assert result.roi_percentage == pytest.approx(-100.0)


class TestEstimateFinancialImpact:
    """Tests for individual financial-impact estimation."""

    def test_calculates_recovered_energy_value(self) -> None:
        result = estimate_financial_impact(
            recovered_energy_kwh=5000.0,
            energy_value_per_kwh=0.12,
        )

        assert result.recovered_energy_value == pytest.approx(600.0)

    def test_calculates_gross_financial_benefit(self) -> None:
        result = estimate_financial_impact(
            recovered_energy_kwh=5000.0,
            energy_value_per_kwh=0.12,
            avoided_failure_cost=4000.0,
            operating_cost_saving=1000.0,
            intervention_cost=2000.0,
        )

        assert result.gross_financial_benefit == pytest.approx(5600.0)

    def test_calculates_net_financial_impact(self) -> None:
        result = estimate_financial_impact(
            recovered_energy_kwh=5000.0,
            energy_value_per_kwh=0.12,
            avoided_failure_cost=4000.0,
            operating_cost_saving=1000.0,
            intervention_cost=2000.0,
        )

        assert result.net_financial_impact == pytest.approx(3600.0)

    def test_calculates_roi(self) -> None:
        result = estimate_financial_impact(
            recovered_energy_kwh=5000.0,
            energy_value_per_kwh=0.12,
            avoided_failure_cost=4000.0,
            operating_cost_saving=1000.0,
            intervention_cost=2000.0,
        )

        assert result.roi_percentage == pytest.approx(180.0)

    def test_zero_intervention_cost_uses_finite_roi_convention(
        self,
    ) -> None:
        result = estimate_financial_impact(
            recovered_energy_kwh=1000.0,
            energy_value_per_kwh=0.10,
            avoided_failure_cost=500.0,
            operating_cost_saving=200.0,
            intervention_cost=0.0,
        )

        assert result.net_financial_impact == pytest.approx(800.0)

        assert result.roi_percentage == pytest.approx(0.0)

    def test_zero_benefits_can_produce_negative_net_impact(
        self,
    ) -> None:
        result = estimate_financial_impact(
            recovered_energy_kwh=0.0,
            energy_value_per_kwh=0.10,
            avoided_failure_cost=0.0,
            operating_cost_saving=0.0,
            intervention_cost=1000.0,
        )

        assert result.gross_financial_benefit == pytest.approx(0.0)

        assert result.net_financial_impact == pytest.approx(-1000.0)

        assert result.roi_percentage == pytest.approx(-100.0)

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("recovered_energy_kwh", math.nan),
            ("energy_value_per_kwh", math.inf),
            ("avoided_failure_cost", -math.inf),
            ("operating_cost_saving", math.nan),
            ("intervention_cost", math.inf),
        ],
    )
    def test_rejects_non_finite_inputs(
        self,
        field_name: str,
        value: float,
    ) -> None:
        inputs = {
            "recovered_energy_kwh": 5000.0,
            "energy_value_per_kwh": 0.12,
            "avoided_failure_cost": 4000.0,
            "operating_cost_saving": 1000.0,
            "intervention_cost": 2000.0,
        }

        inputs[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            estimate_financial_impact(**inputs)

    @pytest.mark.parametrize(
        "field_name",
        [
            "recovered_energy_kwh",
            "energy_value_per_kwh",
            "avoided_failure_cost",
            "operating_cost_saving",
            "intervention_cost",
        ],
    )
    def test_rejects_negative_inputs(
        self,
        field_name: str,
    ) -> None:
        inputs = {
            "recovered_energy_kwh": 5000.0,
            "energy_value_per_kwh": 0.12,
            "avoided_failure_cost": 4000.0,
            "operating_cost_saving": 1000.0,
            "intervention_cost": 2000.0,
        }

        inputs[field_name] = -1.0

        with pytest.raises(
            ValueError,
            match=f"{field_name} must not be negative.",
        ):
            estimate_financial_impact(**inputs)


class TestEstimateFinancialImpacts:
    """Tests for batch financial-impact estimation."""

    def test_adds_financial_columns(self) -> None:
        result = estimate_financial_impacts(frame=_frame())

        assert "recovered_energy_value" in result.columns
        assert "gross_financial_benefit" in result.columns
        assert "net_financial_impact" in result.columns
        assert "roi_percentage" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _frame()

        result = estimate_financial_impacts(frame=frame)

        assert len(result) == len(frame)

    def test_calculates_first_row_correctly(self) -> None:
        result = estimate_financial_impacts(frame=_frame())

        assert result.loc[
            0,
            "recovered_energy_value",
        ] == pytest.approx(600.0)

        assert result.loc[
            0,
            "gross_financial_benefit",
        ] == pytest.approx(5600.0)

        assert result.loc[
            0,
            "net_financial_impact",
        ] == pytest.approx(3600.0)

        assert result.loc[
            0,
            "roi_percentage",
        ] == pytest.approx(180.0)

    def test_handles_zero_cost_row(self) -> None:
        result = estimate_financial_impacts(frame=_frame())

        assert result.loc[
            2,
            "roi_percentage",
        ] == pytest.approx(0.0)

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        estimate_financial_impacts(frame=frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Financial impact frame must not be empty.",
        ):
            estimate_financial_impacts(frame=pd.DataFrame())

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["intervention_cost"])

        with pytest.raises(
            ValueError,
            match=("Financial impact frame is missing required columns"),
        ):
            estimate_financial_impacts(frame=frame)

    def test_rejects_non_numeric_column(self) -> None:
        frame = _frame()

        frame["energy_value_per_kwh"] = [
            "a",
            "b",
            "c",
        ]

        with pytest.raises(
            TypeError,
            match=("Column 'energy_value_per_kwh' must be numeric."),
        ):
            estimate_financial_impacts(frame=frame)

    def test_rejects_missing_numeric_value(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "avoided_failure_cost",
        ] = math.nan

        with pytest.raises(
            ValueError,
            match=("Column 'avoided_failure_cost' must not contain " "missing values."),
        ):
            estimate_financial_impacts(frame=frame)

    def test_rejects_non_finite_numeric_value(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "operating_cost_saving",
        ] = math.inf

        with pytest.raises(
            ValueError,
            match=(
                "Column 'operating_cost_saving' must contain only " "finite values."
            ),
        ):
            estimate_financial_impacts(frame=frame)

    def test_rejects_negative_numeric_value(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "intervention_cost",
        ] = -1.0

        with pytest.raises(
            ValueError,
            match=("Column 'intervention_cost' must not contain " "negative values."),
        ):
            estimate_financial_impacts(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "recovered_energy_kwh": "recovery_kwh",
                "energy_value_per_kwh": "tariff",
                "avoided_failure_cost": "failure_saving",
                "operating_cost_saving": "opex_saving",
                "intervention_cost": "action_cost",
            }
        )

        result = estimate_financial_impacts(
            frame=frame,
            recovered_energy_column="recovery_kwh",
            energy_value_column="tariff",
            avoided_failure_cost_column="failure_saving",
            operating_cost_saving_column="opex_saving",
            intervention_cost_column="action_cost",
        )

        assert "recovered_energy_value" in result.columns
        assert "gross_financial_benefit" in result.columns
        assert "net_financial_impact" in result.columns
        assert "roi_percentage" in result.columns
