"""SHAP explainability for EOIP predictive maintenance."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import shap

from eoip.maintenance.models.failure import RandomForestFailurePredictor


@dataclass(frozen=True, slots=True)
class ShapExplanationResult:
    """SHAP explanation output for failure prediction."""

    values: pd.DataFrame
    base_value: float
    feature_columns: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate SHAP explanation result."""
        if self.values.empty:
            raise ValueError("SHAP values must not be empty.")

        if not self.feature_columns:
            raise ValueError("feature_columns must not be empty.")

        if tuple(self.values.columns) != self.feature_columns:
            raise ValueError("SHAP value columns must match feature_columns.")

        if not np.isfinite(self.values.to_numpy(dtype=float)).all():
            raise ValueError("SHAP values must contain only finite values.")

        if not np.isfinite(self.base_value):
            raise ValueError("base_value must be finite.")

    @property
    def row_count(self) -> int:
        """Return number of explained observations."""
        return len(self.values)

    def mean_absolute_importance(self) -> pd.Series:
        """Return mean absolute SHAP importance by feature."""
        return self.values.abs().mean(axis=0).sort_values(ascending=False)


def explain_failure_predictions(
    *,
    predictor: RandomForestFailurePredictor,
    features: pd.DataFrame,
) -> ShapExplanationResult:
    """Explain Random Forest failure predictions using SHAP."""
    if not predictor.is_fitted:
        raise RuntimeError("Failure predictor must be fitted before explanation.")

    if features.empty:
        raise ValueError("Explanation features must not be empty.")

    if tuple(features.columns) != predictor.feature_columns:
        raise ValueError("Explanation feature columns must match training features.")

    if features.isna().any().any():
        raise ValueError("Explanation features must not contain missing values.")

    non_numeric = [
        column
        for column in features.columns
        if not pd.api.types.is_numeric_dtype(features[column])
    ]

    if non_numeric:
        raise TypeError("Explanation features must be numeric: " f"{non_numeric}")

    values = features.to_numpy(
        dtype=float,
    )

    if not np.isfinite(values).all():
        raise ValueError("Explanation features must contain only finite values.")

    model = predictor._model

    explainer = shap.TreeExplainer(model)

    shap_output = explainer(features)

    shap_values = np.asarray(shap_output.values)

    base_values = np.asarray(shap_output.base_values)

    if shap_values.ndim == 3:
        shap_values = shap_values[:, :, 1]

    if base_values.ndim == 2:
        base_value = float(np.mean(base_values[:, 1]))
    elif base_values.ndim == 1:
        if len(base_values) == len(features):
            base_value = float(np.mean(base_values))
        else:
            base_value = float(base_values[-1])
    else:
        base_value = float(base_values)

    explanation_frame = pd.DataFrame(
        shap_values,
        columns=features.columns,
        index=features.index,
    )

    return ShapExplanationResult(
        values=explanation_frame,
        base_value=base_value,
        feature_columns=tuple(features.columns),
    )
