"""Statistical baseline anomaly detection for EOIP."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from eoip.anomaly.dataset import AnomalyDataset


@dataclass(frozen=True, slots=True)
class StatisticalAnomalyResult:
    """Result produced by the statistical anomaly detector."""

    data: pd.DataFrame
    target_column: str
    threshold: float
    mean: float
    standard_deviation: float

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
        """Return proportion of observations classified as anomalies."""
        if self.row_count == 0:
            return 0.0

        return self.anomaly_count / self.row_count

    def anomalies(self) -> pd.DataFrame:
        """Return detected anomaly observations."""
        return self.data.loc[self.data["is_anomaly"]].copy(deep=True)


class ZScoreAnomalyDetector:
    """Detect anomalies using absolute standard Z-scores."""

    def __init__(self, *, threshold: float = 3.0) -> None:
        """Initialize the detector."""
        if not np.isfinite(threshold):
            raise ValueError("threshold must be finite.")

        if threshold <= 0:
            raise ValueError("threshold must be greater than zero.")

        self._threshold = float(threshold)

    @property
    def threshold(self) -> float:
        """Return configured Z-score threshold."""
        return self._threshold

    def detect(
        self,
        *,
        dataset: AnomalyDataset,
    ) -> StatisticalAnomalyResult:
        """Detect anomalies in a validated anomaly dataset."""
        values = dataset.data[dataset.target_column].to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError("Anomaly target values must be finite.")

        mean = float(np.mean(values))
        standard_deviation = float(np.std(values, ddof=0))

        result = dataset.copy_frame()

        if np.isclose(standard_deviation, 0.0):
            z_scores = np.zeros(
                len(values),
                dtype=float,
            )
        else:
            z_scores = (values - mean) / standard_deviation

        absolute_z_scores = np.abs(z_scores)

        result["z_score"] = z_scores
        result["absolute_z_score"] = absolute_z_scores
        result["is_anomaly"] = absolute_z_scores > self._threshold

        return StatisticalAnomalyResult(
            data=result,
            target_column=dataset.target_column,
            threshold=self._threshold,
            mean=mean,
            standard_deviation=standard_deviation,
        )
