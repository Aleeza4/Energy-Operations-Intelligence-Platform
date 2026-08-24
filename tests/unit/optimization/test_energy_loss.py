"""Unit tests for EOIP energy-loss analysis."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.optimization.energy_loss import (
    EnergyLossResult,
    analyze_energy_losses,
    calculate_energy_loss,
)


def _frame() -> pd.DataFrame:
    """Return deterministic energy-loss inputs."""
    return pd.DataFrame(
        {
            "actual_energy_kwh": [
                800.0,
                1000.0,
                1200.0,
                0.0,
            ],
            "expected_energy_kwh": [
                1000.0,
                1000.0,
                1000.0,
                0.0,
            ],
        }
    )


class TestEnergyLossResult:
    """Tests for individual energy-loss result validation."""

    def test_accepts_valid_result(self) -> None:
        result = EnergyLossResult(
            actual_energy_kwh=800.0,
            expected_energy_kwh=1000.0,
            energy_loss_kwh=200.0,
            loss_percentage=20.0,
        )

        assert result.actual_energy_kwh == pytest.approx(800.0)
        assert result.expected_energy_kwh == pytest.approx(1000.0)
        assert result.energy_loss_kwh == pytest.approx(200.0)
        assert result.loss_percentage == pytest.approx(20.0)

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("actual_energy_kwh", math.nan),
            ("expected_energy_kwh", math.inf),
            ("energy_loss_kwh", -math.inf),
            ("loss_percentage", math.nan),
        ],
    )
    def test_rejects_non_finite_values(
        self,
        field_name: str,
        value: float,
    ) -> None:
        values = {
            "actual_energy_kwh": 800.0,
            "expected_energy_kwh": 1000.0,
            "energy_loss_kwh": 200.0,
            "loss_percentage": 20.0,
        }

        values[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            EnergyLossResult(**values)

    def test_rejects_negative_actual_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match="actual_energy_kwh must not be negative.",
        ):
            EnergyLossResult(
                actual_energy_kwh=-1.0,
                expected_energy_kwh=1000.0,
                energy_loss_kwh=1000.0,
                loss_percentage=100.0,
            )

    def test_rejects_negative_expected_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match="expected_energy_kwh must not be negative.",
        ):
            EnergyLossResult(
                actual_energy_kwh=0.0,
                expected_energy_kwh=-1.0,
                energy_loss_kwh=0.0,
                loss_percentage=0.0,
            )

    def test_rejects_negative_energy_loss(self) -> None:
        with pytest.raises(
            ValueError,
            match="energy_loss_kwh must not be negative.",
        ):
            EnergyLossResult(
                actual_energy_kwh=1000.0,
                expected_energy_kwh=800.0,
                energy_loss_kwh=-200.0,
                loss_percentage=0.0,
            )

    @pytest.mark.parametrize(
        "loss_percentage",
        [
            -0.01,
            100.01,
        ],
    )
    def test_rejects_invalid_loss_percentage(
        self,
        loss_percentage: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="loss_percentage must be between 0 and 100.",
        ):
            EnergyLossResult(
                actual_energy_kwh=800.0,
                expected_energy_kwh=1000.0,
                energy_loss_kwh=200.0,
                loss_percentage=loss_percentage,
            )


class TestCalculateEnergyLoss:
    """Tests for individual energy-loss calculation."""

    def test_calculates_energy_loss(self) -> None:
        result = calculate_energy_loss(
            actual_energy_kwh=800.0,
            expected_energy_kwh=1000.0,
        )

        assert result.energy_loss_kwh == pytest.approx(200.0)

    def test_calculates_loss_percentage(self) -> None:
        result = calculate_energy_loss(
            actual_energy_kwh=800.0,
            expected_energy_kwh=1000.0,
        )

        assert result.loss_percentage == pytest.approx(20.0)

    def test_no_loss_when_actual_equals_expected(self) -> None:
        result = calculate_energy_loss(
            actual_energy_kwh=1000.0,
            expected_energy_kwh=1000.0,
        )

        assert result.energy_loss_kwh == pytest.approx(0.0)
        assert result.loss_percentage == pytest.approx(0.0)

    def test_overperformance_is_clipped_to_zero_loss(self) -> None:
        result = calculate_energy_loss(
            actual_energy_kwh=1200.0,
            expected_energy_kwh=1000.0,
        )

        assert result.energy_loss_kwh == pytest.approx(0.0)
        assert result.loss_percentage == pytest.approx(0.0)

    def test_zero_expected_energy_returns_zero_percentage(self) -> None:
        result = calculate_energy_loss(
            actual_energy_kwh=0.0,
            expected_energy_kwh=0.0,
        )

        assert result.energy_loss_kwh == pytest.approx(0.0)
        assert result.loss_percentage == pytest.approx(0.0)

    def test_zero_actual_energy_is_full_loss(self) -> None:
        result = calculate_energy_loss(
            actual_energy_kwh=0.0,
            expected_energy_kwh=1000.0,
        )

        assert result.energy_loss_kwh == pytest.approx(1000.0)
        assert result.loss_percentage == pytest.approx(100.0)

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("actual_energy_kwh", math.nan),
            ("actual_energy_kwh", math.inf),
            ("expected_energy_kwh", math.nan),
            ("expected_energy_kwh", -math.inf),
        ],
    )
    def test_rejects_non_finite_inputs(
        self,
        field_name: str,
        value: float,
    ) -> None:
        inputs = {
            "actual_energy_kwh": 800.0,
            "expected_energy_kwh": 1000.0,
        }

        inputs[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            calculate_energy_loss(**inputs)

    def test_rejects_negative_actual_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match="actual_energy_kwh must not be negative.",
        ):
            calculate_energy_loss(
                actual_energy_kwh=-1.0,
                expected_energy_kwh=1000.0,
            )

    def test_rejects_negative_expected_energy(self) -> None:
        with pytest.raises(
            ValueError,
            match="expected_energy_kwh must not be negative.",
        ):
            calculate_energy_loss(
                actual_energy_kwh=800.0,
                expected_energy_kwh=-1.0,
            )


class TestAnalyzeEnergyLosses:
    """Tests for batch energy-loss analysis."""

    def test_adds_energy_loss_columns(self) -> None:
        result = analyze_energy_losses(frame=_frame())

        assert "energy_loss_kwh" in result.columns
        assert "loss_percentage" in result.columns

    def test_preserves_row_count(self) -> None:
        frame = _frame()

        result = analyze_energy_losses(frame=frame)

        assert len(result) == len(frame)

    def test_calculates_expected_losses(self) -> None:
        result = analyze_energy_losses(frame=_frame())

        assert result["energy_loss_kwh"].tolist() == pytest.approx(
            [
                200.0,
                0.0,
                0.0,
                0.0,
            ]
        )

    def test_calculates_expected_percentages(self) -> None:
        result = analyze_energy_losses(frame=_frame())

        assert result["loss_percentage"].tolist() == pytest.approx(
            [
                20.0,
                0.0,
                0.0,
                0.0,
            ]
        )

    def test_handles_full_loss(self) -> None:
        frame = pd.DataFrame(
            {
                "actual_energy_kwh": [0.0],
                "expected_energy_kwh": [500.0],
            }
        )

        result = analyze_energy_losses(frame=frame)

        assert result.loc[
            0,
            "energy_loss_kwh",
        ] == pytest.approx(500.0)

        assert result.loc[
            0,
            "loss_percentage",
        ] == pytest.approx(100.0)

    def test_overperformance_is_zero_loss(self) -> None:
        frame = pd.DataFrame(
            {
                "actual_energy_kwh": [1200.0],
                "expected_energy_kwh": [1000.0],
            }
        )

        result = analyze_energy_losses(frame=frame)

        assert result.loc[
            0,
            "energy_loss_kwh",
        ] == pytest.approx(0.0)

        assert result.loc[
            0,
            "loss_percentage",
        ] == pytest.approx(0.0)

    def test_zero_expected_energy_is_safe(self) -> None:
        frame = pd.DataFrame(
            {
                "actual_energy_kwh": [0.0],
                "expected_energy_kwh": [0.0],
            }
        )

        result = analyze_energy_losses(frame=frame)

        assert result.loc[
            0,
            "loss_percentage",
        ] == pytest.approx(0.0)

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()
        original = frame.copy(deep=True)

        analyze_energy_losses(frame=frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Energy loss frame must not be empty.",
        ):
            analyze_energy_losses(frame=pd.DataFrame())

    def test_rejects_empty_actual_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="actual_energy_column must not be empty.",
        ):
            analyze_energy_losses(
                frame=_frame(),
                actual_energy_column=" ",
            )

    def test_rejects_empty_expected_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="expected_energy_column must not be empty.",
        ):
            analyze_energy_losses(
                frame=_frame(),
                expected_energy_column=" ",
            )

    def test_rejects_missing_required_column(self) -> None:
        frame = _frame().drop(columns=["expected_energy_kwh"])

        with pytest.raises(
            ValueError,
            match=("Energy loss frame is missing required columns"),
        ):
            analyze_energy_losses(frame=frame)

    def test_rejects_non_numeric_actual_column(self) -> None:
        frame = _frame()

        frame["actual_energy_kwh"] = [
            "a",
            "b",
            "c",
            "d",
        ]

        with pytest.raises(
            TypeError,
            match="Actual energy column must be numeric.",
        ):
            analyze_energy_losses(frame=frame)

    def test_rejects_non_numeric_expected_column(self) -> None:
        frame = _frame()

        frame["expected_energy_kwh"] = [
            "a",
            "b",
            "c",
            "d",
        ]

        with pytest.raises(
            TypeError,
            match="Expected energy column must be numeric.",
        ):
            analyze_energy_losses(frame=frame)

    def test_rejects_missing_actual_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "actual_energy_kwh",
        ] = math.nan

        with pytest.raises(
            ValueError,
            match=("Actual energy column must not contain missing values."),
        ):
            analyze_energy_losses(frame=frame)

    def test_rejects_missing_expected_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "expected_energy_kwh",
        ] = math.nan

        with pytest.raises(
            ValueError,
            match=("Expected energy column must not contain missing values."),
        ):
            analyze_energy_losses(frame=frame)

    def test_rejects_non_finite_actual_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "actual_energy_kwh",
        ] = math.inf

        with pytest.raises(
            ValueError,
            match=("Actual energy values must contain only finite values."),
        ):
            analyze_energy_losses(frame=frame)

    def test_rejects_non_finite_expected_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "expected_energy_kwh",
        ] = math.inf

        with pytest.raises(
            ValueError,
            match=("Expected energy values must contain only finite values."),
        ):
            analyze_energy_losses(frame=frame)

    def test_rejects_negative_actual_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "actual_energy_kwh",
        ] = -1.0

        with pytest.raises(
            ValueError,
            match=("Actual energy values must not be negative."),
        ):
            analyze_energy_losses(frame=frame)

    def test_rejects_negative_expected_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "expected_energy_kwh",
        ] = -1.0

        with pytest.raises(
            ValueError,
            match=("Expected energy values must not be negative."),
        ):
            analyze_energy_losses(frame=frame)

    def test_supports_custom_column_names(self) -> None:
        frame = _frame().rename(
            columns={
                "actual_energy_kwh": "actual",
                "expected_energy_kwh": "expected",
            }
        )

        result = analyze_energy_losses(
            frame=frame,
            actual_energy_column="actual",
            expected_energy_column="expected",
        )

        assert "energy_loss_kwh" in result.columns
        assert "loss_percentage" in result.columns
