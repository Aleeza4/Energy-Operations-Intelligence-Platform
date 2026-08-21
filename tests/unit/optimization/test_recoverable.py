"""Unit tests for EOIP recoverable-opportunity analysis."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.optimization.recoverable import (
    RecoverableOpportunityResult,
    analyze_recoverable_opportunities,
    calculate_recoverable_opportunity,
)


def _frame() -> pd.DataFrame:
    """Return deterministic recoverable-opportunity inputs."""
    return pd.DataFrame(
        {
            "energy_loss_kwh": [
                1000.0,
                500.0,
                200.0,
                0.0,
            ],
            "recoverability_factor": [
                0.80,
                0.50,
                0.0,
                1.0,
            ],
        }
    )


class TestRecoverableOpportunityResult:
    """Tests for recoverable-opportunity result validation."""

    def test_accepts_valid_result(self) -> None:
        result = RecoverableOpportunityResult(
            energy_loss_kwh=1000.0,
            recoverability_factor=0.80,
            recoverable_energy_kwh=800.0,
            unrecoverable_energy_kwh=200.0,
        )

        assert result.energy_loss_kwh == pytest.approx(1000.0)
        assert result.recoverability_factor == pytest.approx(0.80)
        assert result.recoverable_energy_kwh == pytest.approx(800.0)
        assert result.unrecoverable_energy_kwh == pytest.approx(200.0)

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("energy_loss_kwh", math.nan),
            ("recoverability_factor", math.inf),
            ("recoverable_energy_kwh", -math.inf),
            ("unrecoverable_energy_kwh", math.nan),
        ],
    )
    def test_rejects_non_finite_values(
        self,
        field_name: str,
        value: float,
    ) -> None:
        values = {
            "energy_loss_kwh": 1000.0,
            "recoverability_factor": 0.80,
            "recoverable_energy_kwh": 800.0,
            "unrecoverable_energy_kwh": 200.0,
        }

        values[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            RecoverableOpportunityResult(**values)

    def test_rejects_negative_energy_loss(self) -> None:
        with pytest.raises(
            ValueError,
            match="energy_loss_kwh must not be negative.",
        ):
            RecoverableOpportunityResult(
                energy_loss_kwh=-1.0,
                recoverability_factor=0.50,
                recoverable_energy_kwh=0.0,
                unrecoverable_energy_kwh=0.0,
            )

    @pytest.mark.parametrize(
        "factor",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_recoverability_factor(
        self,
        factor: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="recoverability_factor must be between 0 and 1.",
        ):
            RecoverableOpportunityResult(
                energy_loss_kwh=1000.0,
                recoverability_factor=factor,
                recoverable_energy_kwh=500.0,
                unrecoverable_energy_kwh=500.0,
            )

    def test_rejects_negative_recoverable_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match="recoverable_energy_kwh must not be negative.",
        ):
            RecoverableOpportunityResult(
                energy_loss_kwh=1000.0,
                recoverability_factor=0.50,
                recoverable_energy_kwh=-1.0,
                unrecoverable_energy_kwh=1001.0,
            )

    def test_rejects_negative_unrecoverable_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match="unrecoverable_energy_kwh must not be negative.",
        ):
            RecoverableOpportunityResult(
                energy_loss_kwh=1000.0,
                recoverability_factor=1.0,
                recoverable_energy_kwh=1001.0,
                unrecoverable_energy_kwh=-1.0,
            )

    def test_rejects_energy_reconciliation_mismatch(self) -> None:
        with pytest.raises(
            ValueError,
            match=(
                "Recoverable and unrecoverable energy must sum " "to total energy loss."
            ),
        ):
            RecoverableOpportunityResult(
                energy_loss_kwh=1000.0,
                recoverability_factor=0.50,
                recoverable_energy_kwh=500.0,
                unrecoverable_energy_kwh=400.0,
            )


class TestCalculateRecoverableOpportunity:
    """Tests for individual recoverable-opportunity calculation."""

    def test_calculates_partial_recovery(self) -> None:
        result = calculate_recoverable_opportunity(
            energy_loss_kwh=1000.0,
            recoverability_factor=0.80,
        )

        assert result.recoverable_energy_kwh == pytest.approx(800.0)
        assert result.unrecoverable_energy_kwh == pytest.approx(200.0)

    def test_full_recovery(self) -> None:
        result = calculate_recoverable_opportunity(
            energy_loss_kwh=1000.0,
            recoverability_factor=1.0,
        )

        assert result.recoverable_energy_kwh == pytest.approx(1000.0)
        assert result.unrecoverable_energy_kwh == pytest.approx(0.0)

    def test_zero_recovery(self) -> None:
        result = calculate_recoverable_opportunity(
            energy_loss_kwh=1000.0,
            recoverability_factor=0.0,
        )

        assert result.recoverable_energy_kwh == pytest.approx(0.0)
        assert result.unrecoverable_energy_kwh == pytest.approx(1000.0)

    def test_zero_energy_loss(self) -> None:
        result = calculate_recoverable_opportunity(
            energy_loss_kwh=0.0,
            recoverability_factor=0.75,
        )

        assert result.recoverable_energy_kwh == pytest.approx(0.0)
        assert result.unrecoverable_energy_kwh == pytest.approx(0.0)

    def test_energy_reconciles(self) -> None:
        result = calculate_recoverable_opportunity(
            energy_loss_kwh=1234.5,
            recoverability_factor=0.63,
        )

        assert (
            result.recoverable_energy_kwh + result.unrecoverable_energy_kwh
        ) == pytest.approx(result.energy_loss_kwh)

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("energy_loss_kwh", math.nan),
            ("energy_loss_kwh", math.inf),
            ("recoverability_factor", math.nan),
            ("recoverability_factor", -math.inf),
        ],
    )
    def test_rejects_non_finite_inputs(
        self,
        field_name: str,
        value: float,
    ) -> None:
        inputs = {
            "energy_loss_kwh": 1000.0,
            "recoverability_factor": 0.80,
        }

        inputs[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            calculate_recoverable_opportunity(**inputs)

    def test_rejects_negative_energy_loss(self) -> None:
        with pytest.raises(
            ValueError,
            match="energy_loss_kwh must not be negative.",
        ):
            calculate_recoverable_opportunity(
                energy_loss_kwh=-1.0,
                recoverability_factor=0.50,
            )

    @pytest.mark.parametrize(
        "factor",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_factor_outside_unit_interval(
        self,
        factor: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="recoverability_factor must be between 0 and 1.",
        ):
            calculate_recoverable_opportunity(
                energy_loss_kwh=1000.0,
                recoverability_factor=factor,
            )


class TestAnalyzeRecoverableOpportunities:
    """Tests for batch recoverable-opportunity analysis."""

    def test_adds_output_columns(self) -> None:
        result = analyze_recoverable_opportunities(frame=_frame())

        assert "recoverable_energy_kwh" in result.columns
        assert "unrecoverable_energy_kwh" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _frame()

        result = analyze_recoverable_opportunities(frame=frame)

        assert len(result) == len(frame)

    def test_calculates_expected_recoverable_energy(self) -> None:
        result = analyze_recoverable_opportunities(frame=_frame())

        assert result["recoverable_energy_kwh"].tolist() == pytest.approx(
            [
                800.0,
                250.0,
                0.0,
                0.0,
            ]
        )

    def test_calculates_expected_unrecoverable_energy(self) -> None:
        result = analyze_recoverable_opportunities(frame=_frame())

        assert result["unrecoverable_energy_kwh"].tolist() == pytest.approx(
            [
                200.0,
                250.0,
                200.0,
                0.0,
            ]
        )

    def test_batch_energy_reconciles(self) -> None:
        result = analyze_recoverable_opportunities(frame=_frame())

        reconstructed = (
            result["recoverable_energy_kwh"] + result["unrecoverable_energy_kwh"]
        )

        assert reconstructed.tolist() == pytest.approx(
            result["energy_loss_kwh"].tolist()
        )

    def test_full_recovery_factor(self) -> None:
        frame = pd.DataFrame(
            {
                "energy_loss_kwh": [500.0],
                "recoverability_factor": [1.0],
            }
        )

        result = analyze_recoverable_opportunities(frame=frame)

        assert result.loc[
            0,
            "recoverable_energy_kwh",
        ] == pytest.approx(500.0)

        assert result.loc[
            0,
            "unrecoverable_energy_kwh",
        ] == pytest.approx(0.0)

    def test_zero_recovery_factor(self) -> None:
        frame = pd.DataFrame(
            {
                "energy_loss_kwh": [500.0],
                "recoverability_factor": [0.0],
            }
        )

        result = analyze_recoverable_opportunities(frame=frame)

        assert result.loc[
            0,
            "recoverable_energy_kwh",
        ] == pytest.approx(0.0)

        assert result.loc[
            0,
            "unrecoverable_energy_kwh",
        ] == pytest.approx(500.0)

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        analyze_recoverable_opportunities(frame=frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Recoverable opportunity frame must not be empty."),
        ):
            analyze_recoverable_opportunities(frame=pd.DataFrame())

    def test_rejects_empty_energy_loss_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="energy_loss_column must not be empty.",
        ):
            analyze_recoverable_opportunities(
                frame=_frame(),
                energy_loss_column=" ",
            )

    def test_rejects_empty_recoverability_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match=("recoverability_factor_column must not be empty."),
        ):
            analyze_recoverable_opportunities(
                frame=_frame(),
                recoverability_factor_column=" ",
            )

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["recoverability_factor"])

        with pytest.raises(
            ValueError,
            match=("Recoverable opportunity frame is missing " "required columns"),
        ):
            analyze_recoverable_opportunities(frame=frame)

    def test_rejects_non_numeric_energy_loss(self) -> None:
        frame = _frame()

        frame["energy_loss_kwh"] = [
            "a",
            "b",
            "c",
            "d",
        ]

        with pytest.raises(
            TypeError,
            match="Energy loss column must be numeric.",
        ):
            analyze_recoverable_opportunities(frame=frame)

    def test_rejects_non_numeric_recoverability_factor(
        self,
    ) -> None:
        frame = _frame()

        frame["recoverability_factor"] = [
            "a",
            "b",
            "c",
            "d",
        ]

        with pytest.raises(
            TypeError,
            match=("Recoverability factor column must be numeric."),
        ):
            analyze_recoverable_opportunities(frame=frame)

    def test_rejects_missing_energy_loss(self) -> None:
        frame = _frame()
        frame.loc[0, "energy_loss_kwh"] = math.nan

        with pytest.raises(
            ValueError,
            match=("Energy loss column must not contain missing values."),
        ):
            analyze_recoverable_opportunities(frame=frame)

    def test_rejects_missing_recoverability_factor(
        self,
    ) -> None:
        frame = _frame()
        frame.loc[0, "recoverability_factor"] = math.nan

        with pytest.raises(
            ValueError,
            match=("Recoverability factor column must not contain " "missing values."),
        ):
            analyze_recoverable_opportunities(frame=frame)

    def test_rejects_non_finite_energy_loss(self) -> None:
        frame = _frame()
        frame.loc[0, "energy_loss_kwh"] = math.inf

        with pytest.raises(
            ValueError,
            match=("Energy loss values must contain only finite values."),
        ):
            analyze_recoverable_opportunities(frame=frame)

    def test_rejects_non_finite_recoverability_factor(
        self,
    ) -> None:
        frame = _frame()
        frame.loc[0, "recoverability_factor"] = math.inf

        with pytest.raises(
            ValueError,
            match=("Recoverability factors must contain only finite values."),
        ):
            analyze_recoverable_opportunities(frame=frame)

    def test_rejects_negative_energy_loss(self) -> None:
        frame = _frame()
        frame.loc[0, "energy_loss_kwh"] = -1.0

        with pytest.raises(
            ValueError,
            match="Energy loss values must not be negative.",
        ):
            analyze_recoverable_opportunities(frame=frame)

    @pytest.mark.parametrize(
        "factor",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_recoverability_factor(
        self,
        factor: float,
    ) -> None:
        frame = _frame()
        frame.loc[0, "recoverability_factor"] = factor

        with pytest.raises(
            ValueError,
            match=("Recoverability factors must be between 0 and 1."),
        ):
            analyze_recoverable_opportunities(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "energy_loss_kwh": "lost_energy",
                "recoverability_factor": "recovery_factor",
            }
        )

        result = analyze_recoverable_opportunities(
            frame=frame,
            energy_loss_column="lost_energy",
            recoverability_factor_column="recovery_factor",
        )

        assert "recoverable_energy_kwh" in result.columns
        assert "unrecoverable_energy_kwh" in result.columns
