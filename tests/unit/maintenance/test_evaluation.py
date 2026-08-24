"""Unit tests for EOIP predictive-maintenance model evaluation."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eoip.maintenance.evaluation import (
    MaintenanceEvaluationResult,
    evaluate_failure_predictions,
)


def _actual() -> pd.Series:
    """Return deterministic actual failure labels."""
    return pd.Series(
        [
            0,
            0,
            1,
            1,
            0,
            1,
        ],
        name="actual",
    )


def _predicted() -> pd.Series:
    """Return deterministic predicted failure labels."""
    return pd.Series(
        [
            0,
            1,
            1,
            1,
            0,
            0,
        ],
        name="predicted",
    )


def _probabilities() -> pd.Series:
    """Return deterministic failure probabilities."""
    return pd.Series(
        [
            0.10,
            0.70,
            0.90,
            0.80,
            0.20,
            0.40,
        ],
        name="failure_probability",
    )


class TestMaintenanceEvaluationResult:
    """Tests for predictive-maintenance evaluation result validation."""

    def test_accepts_valid_result(self) -> None:
        result = MaintenanceEvaluationResult(
            accuracy=4 / 6,
            precision=2 / 3,
            recall=2 / 3,
            specificity=2 / 3,
            f1_score=2 / 3,
            roc_auc=0.8,
            true_positives=2,
            true_negatives=2,
            false_positives=1,
            false_negatives=1,
            sample_count=6,
        )

        assert result.sample_count == 6
        assert result.true_positives == 2
        assert result.true_negatives == 2
        assert result.false_positives == 1
        assert result.false_negatives == 1

    @pytest.mark.parametrize(
        "field_name",
        [
            "accuracy",
            "precision",
            "recall",
            "specificity",
            "f1_score",
            "roc_auc",
        ],
    )
    def test_rejects_metric_below_zero(
        self,
        field_name: str,
    ) -> None:
        values = {
            "accuracy": 0.8,
            "precision": 0.8,
            "recall": 0.8,
            "specificity": 0.8,
            "f1_score": 0.8,
            "roc_auc": 0.8,
        }

        values[field_name] = -0.01

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be between 0 and 1.",
        ):
            MaintenanceEvaluationResult(
                **values,
                true_positives=2,
                true_negatives=2,
                false_positives=1,
                false_negatives=1,
                sample_count=6,
            )

    @pytest.mark.parametrize(
        "field_name",
        [
            "accuracy",
            "precision",
            "recall",
            "specificity",
            "f1_score",
            "roc_auc",
        ],
    )
    def test_rejects_metric_above_one(
        self,
        field_name: str,
    ) -> None:
        values = {
            "accuracy": 0.8,
            "precision": 0.8,
            "recall": 0.8,
            "specificity": 0.8,
            "f1_score": 0.8,
            "roc_auc": 0.8,
        }

        values[field_name] = 1.01

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be between 0 and 1.",
        ):
            MaintenanceEvaluationResult(
                **values,
                true_positives=2,
                true_negatives=2,
                false_positives=1,
                false_negatives=1,
                sample_count=6,
            )

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("accuracy", math.nan),
            ("precision", math.inf),
            ("recall", -math.inf),
            ("specificity", math.nan),
            ("f1_score", math.inf),
            ("roc_auc", math.nan),
        ],
    )
    def test_rejects_non_finite_metric(
        self,
        field_name: str,
        value: float,
    ) -> None:
        values = {
            "accuracy": 0.8,
            "precision": 0.8,
            "recall": 0.8,
            "specificity": 0.8,
            "f1_score": 0.8,
            "roc_auc": 0.8,
        }

        values[field_name] = value

        with pytest.raises(
            ValueError,
            match=f"{field_name} must be finite.",
        ):
            MaintenanceEvaluationResult(
                **values,
                true_positives=2,
                true_negatives=2,
                false_positives=1,
                false_negatives=1,
                sample_count=6,
            )

    @pytest.mark.parametrize(
        "field_name",
        [
            "true_positives",
            "true_negatives",
            "false_positives",
            "false_negatives",
            "sample_count",
        ],
    )
    def test_rejects_negative_count(
        self,
        field_name: str,
    ) -> None:
        counts = {
            "true_positives": 2,
            "true_negatives": 2,
            "false_positives": 1,
            "false_negatives": 1,
            "sample_count": 6,
        }

        counts[field_name] = -1

        with pytest.raises(
            ValueError,
            match=f"{field_name} must not be negative.",
        ):
            MaintenanceEvaluationResult(
                accuracy=0.8,
                precision=0.8,
                recall=0.8,
                specificity=0.8,
                f1_score=0.8,
                roc_auc=0.8,
                **counts,
            )

    def test_rejects_confusion_total_mismatch(self) -> None:
        with pytest.raises(
            ValueError,
            match=("Confusion-matrix counts must equal sample_count."),
        ):
            MaintenanceEvaluationResult(
                accuracy=0.8,
                precision=0.8,
                recall=0.8,
                specificity=0.8,
                f1_score=0.8,
                roc_auc=0.8,
                true_positives=2,
                true_negatives=2,
                false_positives=1,
                false_negatives=1,
                sample_count=99,
            )


class TestEvaluateFailurePredictions:
    """Tests for failure-prediction evaluation."""

    def test_returns_expected_confusion_matrix(self) -> None:
        result = evaluate_failure_predictions(
            actual=_actual(),
            predicted=_predicted(),
            probabilities=_probabilities(),
        )

        assert result.true_positives == 2
        assert result.true_negatives == 2
        assert result.false_positives == 1
        assert result.false_negatives == 1
        assert result.sample_count == 6

    def test_accuracy(self) -> None:
        result = evaluate_failure_predictions(
            actual=_actual(),
            predicted=_predicted(),
            probabilities=_probabilities(),
        )

        assert result.accuracy == pytest.approx(4 / 6)

    def test_precision(self) -> None:
        result = evaluate_failure_predictions(
            actual=_actual(),
            predicted=_predicted(),
            probabilities=_probabilities(),
        )

        assert result.precision == pytest.approx(2 / 3)

    def test_recall(self) -> None:
        result = evaluate_failure_predictions(
            actual=_actual(),
            predicted=_predicted(),
            probabilities=_probabilities(),
        )

        assert result.recall == pytest.approx(2 / 3)

    def test_specificity(self) -> None:
        result = evaluate_failure_predictions(
            actual=_actual(),
            predicted=_predicted(),
            probabilities=_probabilities(),
        )

        assert result.specificity == pytest.approx(2 / 3)

    def test_f1_score(self) -> None:
        result = evaluate_failure_predictions(
            actual=_actual(),
            predicted=_predicted(),
            probabilities=_probabilities(),
        )

        assert result.f1_score == pytest.approx(2 / 3)

    def test_roc_auc_is_valid(self) -> None:
        result = evaluate_failure_predictions(
            actual=_actual(),
            predicted=_predicted(),
            probabilities=_probabilities(),
        )

        assert 0.0 <= result.roc_auc <= 1.0

    def test_perfect_predictions(self) -> None:
        actual = pd.Series(
            [
                0,
                1,
                0,
                1,
            ]
        )

        predicted = actual.copy()

        probabilities = pd.Series(
            [
                0.1,
                0.9,
                0.2,
                0.8,
            ]
        )

        result = evaluate_failure_predictions(
            actual=actual,
            predicted=predicted,
            probabilities=probabilities,
        )

        assert result.accuracy == pytest.approx(1.0)
        assert result.precision == pytest.approx(1.0)
        assert result.recall == pytest.approx(1.0)
        assert result.specificity == pytest.approx(1.0)
        assert result.f1_score == pytest.approx(1.0)
        assert result.roc_auc == pytest.approx(1.0)

    def test_zero_division_precision_is_zero(self) -> None:
        actual = pd.Series(
            [
                0,
                1,
                0,
                1,
            ]
        )

        predicted = pd.Series(
            [
                0,
                0,
                0,
                0,
            ]
        )

        probabilities = pd.Series(
            [
                0.1,
                0.4,
                0.2,
                0.3,
            ]
        )

        result = evaluate_failure_predictions(
            actual=actual,
            predicted=predicted,
            probabilities=probabilities,
        )

        assert result.precision == pytest.approx(0.0)

    def test_rejects_empty_actual(self) -> None:
        with pytest.raises(
            ValueError,
            match="Actual failure labels must not be empty.",
        ):
            evaluate_failure_predictions(
                actual=pd.Series(dtype=int),
                predicted=_predicted(),
                probabilities=_probabilities(),
            )

    def test_rejects_empty_predicted(self) -> None:
        with pytest.raises(
            ValueError,
            match="Predicted failure labels must not be empty.",
        ):
            evaluate_failure_predictions(
                actual=_actual(),
                predicted=pd.Series(dtype=int),
                probabilities=_probabilities(),
            )

    def test_rejects_empty_probabilities(self) -> None:
        with pytest.raises(
            ValueError,
            match="Failure probabilities must not be empty.",
        ):
            evaluate_failure_predictions(
                actual=_actual(),
                predicted=_predicted(),
                probabilities=pd.Series(dtype=float),
            )

    def test_rejects_length_mismatch(self) -> None:
        with pytest.raises(
            ValueError,
            match=(
                "Actual labels, predictions, and probabilities "
                "must contain the same number of rows."
            ),
        ):
            evaluate_failure_predictions(
                actual=_actual(),
                predicted=_predicted().iloc[:-1],
                probabilities=_probabilities(),
            )

    def test_rejects_missing_actual_values(self) -> None:
        actual = _actual().astype("Int64")
        actual.iloc[0] = pd.NA

        with pytest.raises(
            ValueError,
            match=("Actual failure labels must not contain missing values."),
        ):
            evaluate_failure_predictions(
                actual=actual,
                predicted=_predicted(),
                probabilities=_probabilities(),
            )

    def test_rejects_missing_predicted_values(self) -> None:
        predicted = _predicted().astype("Int64")
        predicted.iloc[0] = pd.NA

        with pytest.raises(
            ValueError,
            match=("Predicted failure labels must not contain missing values."),
        ):
            evaluate_failure_predictions(
                actual=_actual(),
                predicted=predicted,
                probabilities=_probabilities(),
            )

    def test_rejects_missing_probability_values(self) -> None:
        probabilities = _probabilities()
        probabilities.iloc[0] = math.nan

        with pytest.raises(
            ValueError,
            match=("Failure probabilities must not contain missing values."),
        ):
            evaluate_failure_predictions(
                actual=_actual(),
                predicted=_predicted(),
                probabilities=probabilities,
            )

    def test_rejects_non_binary_actual(self) -> None:
        actual = _actual().copy()
        actual.iloc[0] = 2

        with pytest.raises(
            ValueError,
            match=("Actual failure labels must contain only binary values."),
        ):
            evaluate_failure_predictions(
                actual=actual,
                predicted=_predicted(),
                probabilities=_probabilities(),
            )

    def test_rejects_non_binary_predicted(self) -> None:
        predicted = _predicted().copy()
        predicted.iloc[0] = 2

        with pytest.raises(
            ValueError,
            match=("Predicted failure labels must contain only binary values."),
        ):
            evaluate_failure_predictions(
                actual=_actual(),
                predicted=predicted,
                probabilities=_probabilities(),
            )

    def test_rejects_single_class_actual(self) -> None:
        actual = pd.Series(
            [
                0,
                0,
                0,
                0,
            ]
        )

        predicted = pd.Series(
            [
                0,
                0,
                0,
                0,
            ]
        )

        probabilities = pd.Series(
            [
                0.1,
                0.2,
                0.3,
                0.4,
            ]
        )

        with pytest.raises(
            ValueError,
            match=("Actual failure labels must contain both classes."),
        ):
            evaluate_failure_predictions(
                actual=actual,
                predicted=predicted,
                probabilities=probabilities,
            )

    def test_rejects_non_numeric_probabilities(self) -> None:
        probabilities = pd.Series(
            [
                "low",
                "high",
                "low",
                "high",
                "low",
                "high",
            ]
        )

        with pytest.raises(
            TypeError,
            match="Failure probabilities must be numeric.",
        ):
            evaluate_failure_predictions(
                actual=_actual(),
                predicted=_predicted(),
                probabilities=probabilities,
            )

    @pytest.mark.parametrize(
        "value",
        [
            math.inf,
            -math.inf,
        ],
    )
    def test_rejects_non_finite_probabilities(
        self,
        value: float,
    ) -> None:
        probabilities = _probabilities()
        probabilities.iloc[0] = value

        with pytest.raises(
            ValueError,
            match=("Failure probabilities must contain only finite values."),
        ):
            evaluate_failure_predictions(
                actual=_actual(),
                predicted=_predicted(),
                probabilities=probabilities,
            )

    @pytest.mark.parametrize(
        "value",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_probability_outside_unit_interval(
        self,
        value: float,
    ) -> None:
        probabilities = _probabilities()
        probabilities.iloc[0] = value

        with pytest.raises(
            ValueError,
            match=("Failure probabilities must be between 0 and 1."),
        ):
            evaluate_failure_predictions(
                actual=_actual(),
                predicted=_predicted(),
                probabilities=probabilities,
            )
