"""Isolation Forest anomaly detection for EOIP."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from eoip.anomaly.dataset import AnomalyDataset


@dataclass(frozen=True, slots=True)
class IsolationForestResult:
    """Result produced by the Isolation Forest detector."""

    data: pd.DataFrame
    feature_columns: tuple[str, ...]
    contamination: float | str
    random_state: int

    @property
    def row_count(self) -> int:
        """Return number of evaluated observations."""
        return len(self.data)

    @property
    def anomaly_count(self) -> int:
        """Return number of detected anomalies."""
        return int(self.data["is_anomaly"].sum())

    @property
    def anomaly_rate(self) -> float:
        """Return anomaly proportion."""
        if self.row_count == 0:
            return 0.0

        return self.anomaly_count / self.row_count

    def anomalies(self) -> pd.DataFrame:
        """Return detected anomalies."""
        return self.data.loc[self.data["is_anomaly"]].copy(deep=True)


class IsolationForestAnomalyDetector:
    """Detect multivariate anomalies using Isolation Forest."""

    def __init__(
        self,
        *,
        contamination: float | str = "auto",
        random_state: int = 42,
        n_estimators: int = 100,
    ) -> None:
        """Initialize Isolation Forest detector."""
        if isinstance(contamination, float):
            if not 0.0 < contamination <= 0.5:
                raise ValueError("contamination must be in the interval (0, 0.5].")
        elif contamination != "auto":
            raise ValueError("contamination must be a float or 'auto'.")

        if n_estimators < 1:
            raise ValueError("n_estimators must be greater than zero.")

        self.contamination = contamination
        self.random_state = random_state
        self.n_estimators = n_estimators

        self._model: IsolationForest | None = None
        self._feature_columns: tuple[str, ...] | None = None

    def fit_detect(
        self,
        *,
        dataset: AnomalyDataset,
        feature_columns: list[str] | None = None,
    ) -> IsolationForestResult:
        """Fit Isolation Forest and detect anomalies."""
        if feature_columns is None:
            selected_features = [dataset.target_column]
        else:
            selected_features = list(feature_columns)

        if not selected_features:
            raise ValueError("At least one feature column is required.")

        missing_columns = sorted(set(selected_features) - set(dataset.data.columns))

        if missing_columns:
            raise ValueError(
                "Anomaly feature columns are missing: " f"{missing_columns}"
            )

        feature_frame = dataset.data[selected_features].copy()

        for column in selected_features:
            if not pd.api.types.is_numeric_dtype(feature_frame[column]):
                raise TypeError(f"Feature column must be numeric: {column}")

        if feature_frame.isna().any().any():
            raise ValueError("Anomaly feature columns must not contain missing values.")

        values = feature_frame.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError("Anomaly feature values must be finite.")

        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=self.n_estimators,
        )

        labels = model.fit_predict(values)
        scores = model.decision_function(values)

        result = dataset.copy_frame()

        result["anomaly_score"] = scores.astype(float)
        result["is_anomaly"] = labels == -1

        self._model = model
        self._feature_columns = tuple(selected_features)

        return IsolationForestResult(
            data=result,
            feature_columns=tuple(selected_features),
            contamination=self.contamination,
            random_state=self.random_state,
        )

    @property
    def feature_columns(self) -> tuple[str, ...] | None:
        """Return fitted feature columns."""
        return self._feature_columns
