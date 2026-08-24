"""Unit tests for EOIP residual-based anomaly analysis."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.anomaly.residual import (
    ResidualAnalysisResult,
    analyze_residuals,
)


def _frame() -> pd.DataFrame:
    """Return a valid residual-analysis frame."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                start="2026-08-18T10:00:00Z",
                periods=5,
                freq="15min",
            ),
            "actual_power_kw": [
                100.0,
                110.0,
                120.0,
                200.0,
                130.0,
            ],
            "expected_power_kw": [
                100.0,
                105.0,
                125.0,
                130.0,
                130.0,
            ],
        }
    )


class TestResidualAnalysisResult:
    """Tests for residual analysis result properties."""

    def test_row_count(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert result.row_count == 5

    def test_anomaly_count(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert result.anomaly_count == 1

    def test_anomaly_rate(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert result.anomaly_rate == pytest.approx(0.2)

    def test_anomalies_returns_only_flagged_rows(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        anomalies = result.anomalies()

        assert len(anomalies) == 1
        assert anomalies["actual_power_kw"].iloc[0] == 200.0
        assert anomalies["is_anomaly"].all()

    def test_anomalies_returns_independent_dataframe(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        anomalies = result.anomalies()

        anomalies.loc[
            anomalies.index[0],
            "actual_power_kw",
        ] = 9999.0

        assert 9999.0 not in result.data["actual_power_kw"].tolist()


class TestAnalyzeResiduals:
    """Tests for residual anomaly analysis."""

    def test_returns_residual_analysis_result(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert isinstance(
            result,
            ResidualAnalysisResult,
        )

    def test_calculates_residuals(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert result.data["residual"].tolist() == pytest.approx(
            [
                0.0,
                5.0,
                -5.0,
                70.0,
                0.0,
            ]
        )

    def test_calculates_absolute_residuals(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert result.data["absolute_residual"].tolist() == pytest.approx(
            [
                0.0,
                5.0,
                5.0,
                70.0,
                0.0,
            ]
        )

    def test_flags_expected_anomaly(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert result.data["is_anomaly"].tolist() == [
            False,
            False,
            False,
            True,
            False,
        ]

    def test_uses_strict_threshold_comparison(self) -> None:
        frame = pd.DataFrame(
            {
                "actual": [
                    100.0,
                    110.0,
                ],
                "expected": [
                    90.0,
                    100.0,
                ],
            }
        )

        result = analyze_residuals(
            frame=frame,
            actual_column="actual",
            expected_column="expected",
            threshold=10.0,
        )

        assert result.data["absolute_residual"].tolist() == [
            10.0,
            10.0,
        ]

        assert result.data["is_anomaly"].tolist() == [
            False,
            False,
        ]

    def test_preserves_metadata(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert result.actual_column == "actual_power_kw"
        assert result.expected_column == "expected_power_kw"
        assert result.threshold == pytest.approx(50.0)

    def test_preserves_source_columns(self) -> None:
        result = analyze_residuals(
            frame=_frame(),
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert "timestamp" in result.data.columns
        assert "actual_power_kw" in result.data.columns
        assert "expected_power_kw" in result.data.columns

    def test_does_not_mutate_source_frame(self) -> None:
        frame = _frame()

        analyze_residuals(
            frame=frame,
            actual_column="actual_power_kw",
            expected_column="expected_power_kw",
            threshold=50.0,
        )

        assert "residual" not in frame.columns
        assert "absolute_residual" not in frame.columns
        assert "is_anomaly" not in frame.columns

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Residual analysis frame must not be empty.",
        ):
            analyze_residuals(
                frame=pd.DataFrame(),
                actual_column="actual",
                expected_column="expected",
                threshold=10.0,
            )

    def test_rejects_empty_actual_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="actual_column must not be empty.",
        ):
            analyze_residuals(
                frame=_frame(),
                actual_column=" ",
                expected_column="expected_power_kw",
                threshold=10.0,
            )

    def test_rejects_empty_expected_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="expected_column must not be empty.",
        ):
            analyze_residuals(
                frame=_frame(),
                actual_column="actual_power_kw",
                expected_column=" ",
                threshold=10.0,
            )

    def test_rejects_missing_actual_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing actual column: missing_actual",
        ):
            analyze_residuals(
                frame=_frame(),
                actual_column="missing_actual",
                expected_column="expected_power_kw",
                threshold=10.0,
            )

    def test_rejects_missing_expected_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing expected column: missing_expected",
        ):
            analyze_residuals(
                frame=_frame(),
                actual_column="actual_power_kw",
                expected_column="missing_expected",
                threshold=10.0,
            )

    @pytest.mark.parametrize(
        "threshold",
        [
            0.0,
            -1.0,
            -10.0,
        ],
    )
    def test_rejects_non_positive_threshold(
        self,
        threshold: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="threshold must be greater than zero.",
        ):
            analyze_residuals(
                frame=_frame(),
                actual_column="actual_power_kw",
                expected_column="expected_power_kw",
                threshold=threshold,
            )

    @pytest.mark.parametrize(
        "threshold",
        [
            float("inf"),
            float("-inf"),
            float("nan"),
        ],
    )
    def test_rejects_non_finite_threshold(
        self,
        threshold: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="threshold must be finite.",
        ):
            analyze_residuals(
                frame=_frame(),
                actual_column="actual_power_kw",
                expected_column="expected_power_kw",
                threshold=threshold,
            )

    def test_rejects_non_numeric_actual_column(self) -> None:
        frame = _frame()

        frame["actual_power_kw"] = [
            "a",
            "b",
            "c",
            "d",
            "e",
        ]

        with pytest.raises(
            TypeError,
            match="Actual column must contain numeric values.",
        ):
            analyze_residuals(
                frame=frame,
                actual_column="actual_power_kw",
                expected_column="expected_power_kw",
                threshold=10.0,
            )

    def test_rejects_non_numeric_expected_column(self) -> None:
        frame = _frame()

        frame["expected_power_kw"] = [
            "a",
            "b",
            "c",
            "d",
            "e",
        ]

        with pytest.raises(
            TypeError,
            match="Expected column must contain numeric values.",
        ):
            analyze_residuals(
                frame=frame,
                actual_column="actual_power_kw",
                expected_column="expected_power_kw",
                threshold=10.0,
            )

    def test_rejects_missing_actual_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "actual_power_kw",
        ] = float("nan")

        with pytest.raises(
            ValueError,
            match="Actual column must not contain missing values.",
        ):
            analyze_residuals(
                frame=frame,
                actual_column="actual_power_kw",
                expected_column="expected_power_kw",
                threshold=10.0,
            )

    def test_rejects_missing_expected_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "expected_power_kw",
        ] = float("nan")

        with pytest.raises(
            ValueError,
            match="Expected column must not contain missing values.",
        ):
            analyze_residuals(
                frame=frame,
                actual_column="actual_power_kw",
                expected_column="expected_power_kw",
                threshold=10.0,
            )

    def test_rejects_non_finite_actual_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "actual_power_kw",
        ] = float("inf")

        with pytest.raises(
            ValueError,
            match="Actual values must be finite.",
        ):
            analyze_residuals(
                frame=frame,
                actual_column="actual_power_kw",
                expected_column="expected_power_kw",
                threshold=10.0,
            )

    def test_rejects_non_finite_expected_values(self) -> None:
        frame = _frame()

        frame.loc[
            0,
            "expected_power_kw",
        ] = float("inf")

        with pytest.raises(
            ValueError,
            match="Expected values must be finite.",
        ):
            analyze_residuals(
                frame=frame,
                actual_column="actual_power_kw",
                expected_column="expected_power_kw",
                threshold=10.0,
            )
