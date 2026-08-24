"""Failure-prediction models for EOIP predictive maintenance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


@dataclass(frozen=True, slots=True)
class FailurePredictionResult:
    """Predictions produced by a predictive-maintenance classifier."""

    predictions: pd.DataFrame
    model_name: str
    target_column: str
    probability_column: str = "failure_probability"
    prediction_column: str = "predicted_failure"

    def __post_init__(self) -> None:
        """Validate prediction output."""
        if self.predictions.empty:
            raise ValueError("Failure predictions must not be empty.")

        if not self.model_name.strip():
            raise ValueError("model_name must not be empty.")

        if not self.target_column.strip():
            raise ValueError("target_column must not be empty.")

        required_columns = {
            self.probability_column,
            self.prediction_column,
        }

        missing_columns = required_columns - set(self.predictions.columns)

        if missing_columns:
            raise ValueError(
                "Failure predictions are missing required columns: "
                f"{sorted(missing_columns)}"
            )

        probabilities = self.predictions[self.probability_column]

        if probabilities.isna().any():
            raise ValueError("Failure probabilities must not contain missing values.")

        if not pd.api.types.is_numeric_dtype(probabilities):
            raise TypeError("Failure probabilities must be numeric.")

        if ((probabilities < 0.0) | (probabilities > 1.0)).any():
            raise ValueError("Failure probabilities must be between 0 and 1.")

        predictions = self.predictions[self.prediction_column]

        if predictions.isna().any():
            raise ValueError("Failure predictions must not contain missing values.")

    @property
    def row_count(self) -> int:
        """Return number of predictions."""
        return len(self.predictions)

    @property
    def predicted_failure_count(self) -> int:
        """Return number of observations predicted to fail."""
        return int(self.predictions[self.prediction_column].astype(bool).sum())


class FailurePredictor(Protocol):
    """Interface implemented by failure-prediction models."""

    @property
    def model_name(self) -> str:
        """Return human-readable model name."""
        ...

    def fit(
        self,
        features: pd.DataFrame,
        target: pd.Series,
    ) -> None:
        """Train the failure-prediction model."""
        ...

    def predict(
        self,
        features: pd.DataFrame,
    ) -> FailurePredictionResult:
        """Predict future equipment failures."""
        ...


class RandomForestFailurePredictor:
    """Random Forest classifier for equipment failure prediction."""

    def __init__(
        self,
        *,
        n_estimators: int = 100,
        max_depth: int | None = None,
        random_state: int = 42,
        probability_threshold: float = 0.5,
        class_weight: str | dict[int, float] | None = "balanced",
    ) -> None:
        """Initialize the Random Forest failure predictor."""
        if n_estimators < 1:
            raise ValueError("n_estimators must be greater than zero.")

        if max_depth is not None and max_depth < 1:
            raise ValueError("max_depth must be greater than zero when provided.")

        if not 0.0 <= probability_threshold <= 1.0:
            raise ValueError("probability_threshold must be between 0 and 1.")

        self._probability_threshold = probability_threshold

        self._model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            class_weight=class_weight,
        )

        self._feature_columns: tuple[str, ...] | None = None
        self._target_column = "failure_within_window"
        self._is_fitted = False

    @property
    def model_name(self) -> str:
        """Return model name."""
        return "Random Forest"

    @property
    def feature_columns(self) -> tuple[str, ...]:
        """Return features used during training."""
        if self._feature_columns is None:
            return ()

        return self._feature_columns

    @property
    def is_fitted(self) -> bool:
        """Return whether the model has been trained."""
        return self._is_fitted

    @property
    def estimator(self) -> RandomForestClassifier:
        """Return the underlying fitted Random Forest estimator."""
        if not self._is_fitted:
            raise RuntimeError(
                "Failure predictor must be fitted before accessing estimator."
            )

        return self._model

    def fit(
        self,
        features: pd.DataFrame,
        target: pd.Series,
    ) -> None:
        """Train the Random Forest failure classifier."""
        self._validate_features(features)

        if target.empty:
            raise ValueError("Failure target must not be empty.")

        if len(features) != len(target):
            raise ValueError(
                "Features and target must contain the same number of rows."
            )

        if target.isna().any():
            raise ValueError("Failure target must not contain missing values.")

        normalized_target = target.astype(int)

        unique_classes = set(normalized_target.unique().tolist())

        if not unique_classes.issubset({0, 1}):
            raise ValueError("Failure target must contain only binary values.")

        if len(unique_classes) < 2:
            raise ValueError("Failure target must contain both classes.")

        self._feature_columns = tuple(features.columns)

        self._model.fit(
            features,
            normalized_target,
        )

        self._is_fitted = True

    def predict(
        self,
        features: pd.DataFrame,
    ) -> FailurePredictionResult:
        """Predict future failures and probabilities."""
        if not self._is_fitted:
            raise RuntimeError("Failure predictor must be fitted before prediction.")

        self._validate_features(features)

        expected_columns = self.feature_columns

        if tuple(features.columns) != expected_columns:
            raise ValueError("Prediction feature columns must match training features.")

        probabilities = self._model.predict_proba(features)[:, 1]

        predicted = probabilities >= self._probability_threshold

        result = pd.DataFrame(
            {
                "failure_probability": probabilities,
                "predicted_failure": predicted,
            },
            index=features.index,
        )

        return FailurePredictionResult(
            predictions=result,
            model_name=self.model_name,
            target_column=self._target_column,
        )

    @staticmethod
    def _validate_features(
        features: pd.DataFrame,
    ) -> None:
        """Validate model feature matrix."""
        if features.empty:
            raise ValueError("Failure prediction features must not be empty.")

        if features.columns.empty:
            raise ValueError("Failure prediction requires at least one feature.")

        if features.columns.duplicated().any():
            raise ValueError("Failure prediction feature names must be unique.")

        non_numeric = [
            column
            for column in features.columns
            if not pd.api.types.is_numeric_dtype(features[column])
        ]

        if non_numeric:
            raise TypeError(
                "Failure prediction features must be numeric: " f"{non_numeric}"
            )

        if features.isna().any().any():
            raise ValueError(
                "Failure prediction features must not contain " "missing values."
            )

        values = features.to_numpy(
            dtype=float,
        )

        if not np.isfinite(values).all():
            raise ValueError(
                "Failure prediction features must contain only " "finite values."
            )
