"""Unit tests for EOIP anomaly ground-truth evaluation."""

from __future__ import annotations

import pandas as pd
import pytest

from eoip.anomaly.evaluation import (
    GroundTruthEvaluation,
    evaluate_ground_truth,
)


def _frame() -> pd.DataFrame:
    """Return a deterministic evaluation frame."""
    return pd.DataFrame(
        {
            "is_anomaly": [
                True,
                False,
                True,
                False,
                True,
                False,
            ],
            "is_anomaly_ground_truth": [
                True,
                False,
                False,
                True,
                True,
                False,
            ],
        }
    )


class TestGroundTruthEvaluation:
    """Tests for confusion-matrix result properties."""

    def test_total(self) -> None:
        result = GroundTruthEvaluation(
            true_positives=2,
            true_negatives=2,
            false_positives=1,
            false_negatives=1,
        )

        assert result.total == 6

    def test_actual_anomalies(self) -> None:
        result = GroundTruthEvaluation(
            true_positives=2,
            true_negatives=2,
            false_positives=1,
            false_negatives=1,
        )

        assert result.actual_anomalies == 3

    def test_predicted_anomalies(self) -> None:
        result = GroundTruthEvaluation(
            true_positives=2,
            true_negatives=2,
            false_positives=1,
            false_negatives=1,
        )

        assert result.predicted_anomalies == 3

    def test_correct_predictions(self) -> None:
        result = GroundTruthEvaluation(
            true_positives=2,
            true_negatives=2,
            false_positives=1,
            false_negatives=1,
        )

        assert result.correct_predictions == 4

    def test_accuracy(self) -> None:
        result = GroundTruthEvaluation(
            true_positives=2,
            true_negatives=2,
            false_positives=1,
            false_negatives=1,
        )

        assert result.accuracy == pytest.approx(4 / 6)

    def test_zero_total_returns_zero_accuracy(self) -> None:
        result = GroundTruthEvaluation(
            true_positives=0,
            true_negatives=0,
            false_positives=0,
            false_negatives=0,
        )

        assert result.total == 0
        assert result.accuracy == pytest.approx(0.0)


class TestEvaluateGroundTruth:
    """Tests for ground-truth anomaly evaluation."""

    def test_calculates_confusion_matrix(self) -> None:
        result = evaluate_ground_truth(
            frame=_frame(),
        )

        assert result.true_positives == 2
        assert result.true_negatives == 2
        assert result.false_positives == 1
        assert result.false_negatives == 1

    def test_calculates_summary_properties(self) -> None:
        result = evaluate_ground_truth(
            frame=_frame(),
        )

        assert result.total == 6
        assert result.actual_anomalies == 3
        assert result.predicted_anomalies == 3
        assert result.correct_predictions == 4
        assert result.accuracy == pytest.approx(4 / 6)

    def test_supports_custom_column_names(self) -> None:
        frame = pd.DataFrame(
            {
                "predicted": [
                    True,
                    False,
                    True,
                ],
                "truth": [
                    True,
                    False,
                    False,
                ],
            }
        )

        result = evaluate_ground_truth(
            frame=frame,
            predicted_column="predicted",
            ground_truth_column="truth",
        )

        assert result.true_positives == 1
        assert result.true_negatives == 1
        assert result.false_positives == 1
        assert result.false_negatives == 0

    def test_all_predictions_correct(self) -> None:
        frame = pd.DataFrame(
            {
                "is_anomaly": [
                    True,
                    False,
                    True,
                    False,
                ],
                "is_anomaly_ground_truth": [
                    True,
                    False,
                    True,
                    False,
                ],
            }
        )

        result = evaluate_ground_truth(
            frame=frame,
        )

        assert result.true_positives == 2
        assert result.true_negatives == 2
        assert result.false_positives == 0
        assert result.false_negatives == 0
        assert result.accuracy == pytest.approx(1.0)

    def test_all_predictions_wrong(self) -> None:
        frame = pd.DataFrame(
            {
                "is_anomaly": [
                    True,
                    False,
                    True,
                    False,
                ],
                "is_anomaly_ground_truth": [
                    False,
                    True,
                    False,
                    True,
                ],
            }
        )

        result = evaluate_ground_truth(
            frame=frame,
        )

        assert result.true_positives == 0
        assert result.true_negatives == 0
        assert result.false_positives == 2
        assert result.false_negatives == 2
        assert result.accuracy == pytest.approx(0.0)

    def test_no_anomalies_present(self) -> None:
        frame = pd.DataFrame(
            {
                "is_anomaly": [
                    False,
                    False,
                    False,
                ],
                "is_anomaly_ground_truth": [
                    False,
                    False,
                    False,
                ],
            }
        )

        result = evaluate_ground_truth(
            frame=frame,
        )

        assert result.true_positives == 0
        assert result.true_negatives == 3
        assert result.false_positives == 0
        assert result.false_negatives == 0

    def test_rejects_empty_frame(self) -> None:
        with pytest.raises(
            ValueError,
            match="Evaluation frame must not be empty.",
        ):
            evaluate_ground_truth(
                frame=pd.DataFrame(),
            )

    def test_rejects_empty_predicted_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="predicted_column must not be empty.",
        ):
            evaluate_ground_truth(
                frame=_frame(),
                predicted_column=" ",
            )

    def test_rejects_empty_ground_truth_column_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="ground_truth_column must not be empty.",
        ):
            evaluate_ground_truth(
                frame=_frame(),
                ground_truth_column=" ",
            )

    def test_rejects_missing_predicted_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing predicted column: missing_prediction",
        ):
            evaluate_ground_truth(
                frame=_frame(),
                predicted_column="missing_prediction",
            )

    def test_rejects_missing_ground_truth_column(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing ground truth column: missing_truth",
        ):
            evaluate_ground_truth(
                frame=_frame(),
                ground_truth_column="missing_truth",
            )

    def test_rejects_missing_predicted_values(self) -> None:
        frame = _frame().copy()

        frame["is_anomaly"] = frame["is_anomaly"].astype("boolean")

        frame.loc[
            0,
            "is_anomaly",
        ] = pd.NA

        with pytest.raises(
            ValueError,
            match=("Predicted anomaly column must not contain " "missing values."),
        ):
            evaluate_ground_truth(
                frame=frame,
            )

    def test_rejects_missing_ground_truth_values(self) -> None:
        frame = _frame().copy()

        frame["is_anomaly_ground_truth"] = frame["is_anomaly_ground_truth"].astype(
            "boolean"
        )

        frame.loc[
            0,
            "is_anomaly_ground_truth",
        ] = pd.NA

        with pytest.raises(
            ValueError,
            match=("Ground truth anomaly column must not contain " "missing values."),
        ):
            evaluate_ground_truth(
                frame=frame,
            )

    def test_rejects_non_boolean_predicted_column(self) -> None:
        frame = _frame().copy()

        frame["is_anomaly"] = [
            1,
            0,
            1,
            0,
            1,
            0,
        ]

        with pytest.raises(
            TypeError,
            match="Predicted anomaly column must be boolean.",
        ):
            evaluate_ground_truth(
                frame=frame,
            )

    def test_rejects_non_boolean_ground_truth_column(self) -> None:
        frame = _frame().copy()

        frame["is_anomaly_ground_truth"] = [
            1,
            0,
            0,
            1,
            1,
            0,
        ]

        with pytest.raises(
            TypeError,
            match="Ground truth anomaly column must be boolean.",
        ):
            evaluate_ground_truth(
                frame=frame,
            )
