"""EOIP anomaly detection package."""

from eoip.anomaly.dataset import (
    AnomalyDataset,
    AnomalyTarget,
    build_anomaly_dataset,
)

__all__ = [
    "AnomalyDataset",
    "AnomalyTarget",
    "build_anomaly_dataset",
]
