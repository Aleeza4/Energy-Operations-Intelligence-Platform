"""Unit tests for EOIP predictive-maintenance failure prediction."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from eoip.maintenance.models.failure import (
    FailurePredictionResult,
    RandomForestFailurePredictor,
)


def _features() -> pd.DataFrame:
    """Return deterministic predictive-maintenance features."""
    return pd.DataFrame(
        {
            "active_power_kw": [
                500.0,
                490.0,
                480.0,
                300.0,
                280.0,
                260.0,
                520.0,
                510.0,
            ],
            "temperature_c": [
                40.0,
                41.0,
                42.0,
                70.0,
                75.0,
                80.0,
                39.0,
                40.0,
            ],
            "alarm_count": [
                0.0,
                0.0,
                1.0,
                6.0,
                8.0,
                10.0,
                0.0,
                1.0,
            ],
        }
    )


def _target() -> pd.Series:
    """Return deterministic binary failure labels."""
    return pd.Series(
        [
            0,
            0,
            0,
            1,
            1,
            1,
            0,
            0,
        ],
        name="failure_within_window",
    )


def _fitted_predictor(
    *,
    probability_threshold: float = 0.5,
) -> RandomForestFailurePredictor:
    """Return a fitted deterministic Random Forest predictor."""
    predictor = RandomForestFailurePredictor(
        n_estimators=50,
        max_depth=4,
        random_state=42,
        probability_threshold=probability_threshold,
    )

    predictor.fit(
        _features(),
        _target(),
    )

    return predictor


class TestFailurePredictionResult:
    """Tests for failure prediction result validation."""

    def test_accepts_valid_result(self) -> None:
        predictions = pd.DataFrame(
            {
                "failure_probability": [
                    0.1,
                    0.8,
                ],
                "predicted_failure": [
                    False,
                    True,
                ],
            }
        )

        result = FailurePredictionResult(
            predictions=predictions,
            model_name="Random Forest",
            target_column="failure_within_window",
        )

        assert result.row_count == 2
        assert result.predicted_failure_count == 1

    def test_rejects_empty_predictions(self) -> None:
        with pytest.raises(
            ValueError,
            match="Failure predictions must not be empty.",
        ):
            FailurePredictionResult(
                predictions=pd.DataFrame(),
                model_name="Random Forest",
                target_column="failure_within_window",
            )

    def test_rejects_empty_model_name(self) -> None:
        predictions = pd.DataFrame(
            {
                "failure_probability": [0.5],
                "predicted_failure": [True],
            }
        )

        with pytest.raises(
            ValueError,
            match="model_name must not be empty.",
        ):
            FailurePredictionResult(
                predictions=predictions,
                model_name=" ",
                target_column="failure_within_window",
            )

    def test_rejects_empty_target_column(self) -> None:
        predictions = pd.DataFrame(
            {
                "failure_probability": [0.5],
                "predicted_failure": [True],
            }
        )

        with pytest.raises(
            ValueError,
            match="target_column must not be empty.",
        ):
            FailurePredictionResult(
                predictions=predictions,
                model_name="Random Forest",
                target_column=" ",
            )

    def test_rejects_missing_probability_column(self) -> None:
        predictions = pd.DataFrame(
            {
                "predicted_failure": [True],
            }
        )

        with pytest.raises(
            ValueError,
            match=("Failure predictions are missing required columns"),
        ):
            FailurePredictionResult(
                predictions=predictions,
                model_name="Random Forest",
                target_column="failure_within_window",
            )

    def test_rejects_missing_prediction_column(self) -> None:
        predictions = pd.DataFrame(
            {
                "failure_probability": [0.5],
            }
        )

        with pytest.raises(
            ValueError,
            match=("Failure predictions are missing required columns"),
        ):
            FailurePredictionResult(
                predictions=predictions,
                model_name="Random Forest",
                target_column="failure_within_window",
            )

    def test_rejects_missing_probability(self) -> None:
        predictions = pd.DataFrame(
            {
                "failure_probability": [
                    0.1,
                    np.nan,
                ],
                "predicted_failure": [
                    False,
                    True,
                ],
            }
        )

        with pytest.raises(
            ValueError,
            match=("Failure probabilities must not contain missing values."),
        ):
            FailurePredictionResult(
                predictions=predictions,
                model_name="Random Forest",
                target_column="failure_within_window",
            )

    def test_rejects_non_numeric_probability(self) -> None:
        predictions = pd.DataFrame(
            {
                "failure_probability": [
                    "low",
                    "high",
                ],
                "predicted_failure": [
                    False,
                    True,
                ],
            }
        )

        with pytest.raises(
            TypeError,
            match="Failure probabilities must be numeric.",
        ):
            FailurePredictionResult(
                predictions=predictions,
                model_name="Random Forest",
                target_column="failure_within_window",
            )

    @pytest.mark.parametrize(
        "probability",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_probability_outside_unit_interval(
        self,
        probability: float,
    ) -> None:
        predictions = pd.DataFrame(
            {
                "failure_probability": [
                    probability,
                ],
                "predicted_failure": [
                    True,
                ],
            }
        )

        with pytest.raises(
            ValueError,
            match=("Failure probabilities must be between 0 and 1."),
        ):
            FailurePredictionResult(
                predictions=predictions,
                model_name="Random Forest",
                target_column="failure_within_window",
            )

    def test_rejects_missing_prediction(self) -> None:
        predictions = pd.DataFrame(
            {
                "failure_probability": [
                    0.2,
                    0.8,
                ],
                "predicted_failure": pd.Series(
                    [
                        False,
                        pd.NA,
                    ],
                    dtype="boolean",
                ),
            }
        )

        with pytest.raises(
            ValueError,
            match=("Failure predictions must not contain missing values."),
        ):
            FailurePredictionResult(
                predictions=predictions,
                model_name="Random Forest",
                target_column="failure_within_window",
            )


class TestRandomForestFailurePredictorConfiguration:
    """Tests for predictor configuration."""

    def test_default_model_name(self) -> None:
        predictor = RandomForestFailurePredictor()

        assert predictor.model_name == "Random Forest"

    def test_starts_unfitted(self) -> None:
        predictor = RandomForestFailurePredictor()

        assert predictor.is_fitted is False
        assert predictor.feature_columns == ()

    @pytest.mark.parametrize(
        "n_estimators",
        [
            0,
            -1,
        ],
    )
    def test_rejects_invalid_n_estimators(
        self,
        n_estimators: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="n_estimators must be greater than zero.",
        ):
            RandomForestFailurePredictor(n_estimators=n_estimators)

    @pytest.mark.parametrize(
        "max_depth",
        [
            0,
            -1,
        ],
    )
    def test_rejects_invalid_max_depth(
        self,
        max_depth: int,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=("max_depth must be greater than zero when provided."),
        ):
            RandomForestFailurePredictor(max_depth=max_depth)

    @pytest.mark.parametrize(
        "threshold",
        [
            -0.01,
            1.01,
        ],
    )
    def test_rejects_invalid_probability_threshold(
        self,
        threshold: float,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=("probability_threshold must be between 0 and 1."),
        ):
            RandomForestFailurePredictor(probability_threshold=threshold)


class TestRandomForestFailurePredictorFit:
    """Tests for Random Forest model training."""

    def test_fit_marks_model_as_fitted(self) -> None:
        predictor = RandomForestFailurePredictor(random_state=42)

        predictor.fit(
            _features(),
            _target(),
        )

        assert predictor.is_fitted is True

    def test_fit_records_feature_columns(self) -> None:
        predictor = RandomForestFailurePredictor(random_state=42)

        predictor.fit(
            _features(),
            _target(),
        )

        assert predictor.feature_columns == (
            "active_power_kw",
            "temperature_c",
            "alarm_count",
        )

    def test_rejects_empty_features(self) -> None:
        predictor = RandomForestFailurePredictor()

        with pytest.raises(
            ValueError,
            match=("Failure prediction features must not be empty."),
        ):
            predictor.fit(
                pd.DataFrame(),
                _target(),
            )

    def test_rejects_empty_target(self) -> None:
        predictor = RandomForestFailurePredictor()

        with pytest.raises(
            ValueError,
            match="Failure target must not be empty.",
        ):
            predictor.fit(
                _features(),
                pd.Series(dtype=int),
            )

    def test_rejects_different_feature_target_lengths(
        self,
    ) -> None:
        predictor = RandomForestFailurePredictor()

        with pytest.raises(
            ValueError,
            match=("Features and target must contain the same " "number of rows."),
        ):
            predictor.fit(
                _features(),
                _target().iloc[:-1],
            )

    def test_rejects_missing_target_values(self) -> None:
        predictor = RandomForestFailurePredictor()

        target = _target().astype("Int64")
        target.iloc[0] = pd.NA

        with pytest.raises(
            ValueError,
            match=("Failure target must not contain missing values."),
        ):
            predictor.fit(
                _features(),
                target,
            )

    def test_rejects_non_binary_target(self) -> None:
        predictor = RandomForestFailurePredictor()

        target = _target().copy()
        target.iloc[0] = 2

        with pytest.raises(
            ValueError,
            match=("Failure target must contain only binary values."),
        ):
            predictor.fit(
                _features(),
                target,
            )

    def test_rejects_single_class_target(self) -> None:
        predictor = RandomForestFailurePredictor()

        target = pd.Series(
            [0] * len(_features()),
            name="failure_within_window",
        )

        with pytest.raises(
            ValueError,
            match=("Failure target must contain both classes."),
        ):
            predictor.fit(
                _features(),
                target,
            )

    def test_rejects_non_numeric_feature(self) -> None:
        predictor = RandomForestFailurePredictor()

        features = _features()
        features["status"] = "normal"

        with pytest.raises(
            TypeError,
            match=("Failure prediction features must be numeric"),
        ):
            predictor.fit(
                features,
                _target(),
            )

    def test_rejects_missing_feature_value(self) -> None:
        predictor = RandomForestFailurePredictor()

        features = _features()
        features.loc[0, "active_power_kw"] = np.nan

        with pytest.raises(
            ValueError,
            match=("Failure prediction features must not contain " "missing values."),
        ):
            predictor.fit(
                features,
                _target(),
            )

    def test_rejects_infinite_feature_value(self) -> None:
        predictor = RandomForestFailurePredictor()

        features = _features()
        features.loc[
            0,
            "active_power_kw",
        ] = np.inf

        with pytest.raises(
            ValueError,
            match=("Failure prediction features must contain only " "finite values."),
        ):
            predictor.fit(
                features,
                _target(),
            )


class TestRandomForestFailurePredictorPredict:
    """Tests for Random Forest failure prediction."""

    def test_predict_returns_result(self) -> None:
        predictor = _fitted_predictor()

        result = predictor.predict(_features())

        assert isinstance(
            result,
            FailurePredictionResult,
        )

        assert result.model_name == "Random Forest"

        assert result.target_column == "failure_within_window"

    def test_predict_returns_one_row_per_observation(
        self,
    ) -> None:
        predictor = _fitted_predictor()

        result = predictor.predict(_features())

        assert result.row_count == len(_features())

    def test_probabilities_are_between_zero_and_one(
        self,
    ) -> None:
        predictor = _fitted_predictor()

        result = predictor.predict(_features())

        probabilities = result.predictions["failure_probability"]

        assert probabilities.between(
            0.0,
            1.0,
        ).all()

    def test_predictions_are_boolean(self) -> None:
        predictor = _fitted_predictor()

        result = predictor.predict(_features())

        assert pd.api.types.is_bool_dtype(result.predictions["predicted_failure"])

    def test_prediction_threshold_is_applied(self) -> None:
        predictor = _fitted_predictor(probability_threshold=1.0)

        result = predictor.predict(_features())

        probabilities = result.predictions["failure_probability"]

        predicted = result.predictions["predicted_failure"]

        expected = probabilities >= 1.0

        pd.testing.assert_series_equal(
            predicted,
            expected,
            check_names=False,
        )

    def test_prediction_preserves_feature_index(self) -> None:
        predictor = _fitted_predictor()

        features = _features()
        features.index = [
            10,
            20,
            30,
            40,
            50,
            60,
            70,
            80,
        ]

        result = predictor.predict(features)

        assert result.predictions.index.tolist() == [
            10,
            20,
            30,
            40,
            50,
            60,
            70,
            80,
        ]

    def test_predict_before_fit_raises(self) -> None:
        predictor = RandomForestFailurePredictor()

        with pytest.raises(
            RuntimeError,
            match=("Failure predictor must be fitted before prediction."),
        ):
            predictor.predict(_features())

    def test_rejects_prediction_schema_mismatch(self) -> None:
        predictor = _fitted_predictor()

        features = _features()[
            [
                "temperature_c",
                "active_power_kw",
                "alarm_count",
            ]
        ]

        with pytest.raises(
            ValueError,
            match=("Prediction feature columns must match " "training features."),
        ):
            predictor.predict(features)

    def test_deterministic_with_same_random_state(self) -> None:
        first = RandomForestFailurePredictor(
            n_estimators=50,
            random_state=42,
        )

        second = RandomForestFailurePredictor(
            n_estimators=50,
            random_state=42,
        )

        first.fit(
            _features(),
            _target(),
        )

        second.fit(
            _features(),
            _target(),
        )

        first_result = first.predict(_features())

        second_result = second.predict(_features())

        np.testing.assert_allclose(
            first_result.predictions["failure_probability"].to_numpy(),
            second_result.predictions["failure_probability"].to_numpy(),
        )

        pd.testing.assert_series_equal(
            first_result.predictions["predicted_failure"],
            second_result.predictions["predicted_failure"],
        )
