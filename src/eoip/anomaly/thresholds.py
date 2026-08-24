"""Threshold management for EOIP anomaly detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class ThresholdType(StrEnum):
    """Supported anomaly threshold types."""

    Z_SCORE = "z_score"
    RESIDUAL = "residual"
    ANOMALY_SCORE = "anomaly_score"


@dataclass(frozen=True, slots=True)
class AnomalyThreshold:
    """Named anomaly detection threshold."""

    name: str
    threshold_type: ThresholdType
    value: float
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate threshold configuration."""
        if not self.name.strip():
            raise ValueError("name must not be empty.")

        if not np.isfinite(self.value):
            raise ValueError("value must be finite.")

        if (
            self.threshold_type
            in {
                ThresholdType.Z_SCORE,
                ThresholdType.RESIDUAL,
            }
            and self.value <= 0
        ):
            raise ValueError(
                f"{self.threshold_type.value} threshold " "must be greater than zero."
            )


class ThresholdRegistry:
    """Manage named anomaly thresholds."""

    def __init__(self) -> None:
        """Initialize an empty threshold registry."""
        self._thresholds: dict[str, AnomalyThreshold] = {}

    def register(
        self,
        threshold: AnomalyThreshold,
    ) -> None:
        """Register a new threshold."""
        if threshold.name in self._thresholds:
            raise ValueError(f"Threshold already exists: {threshold.name}")

        self._thresholds[threshold.name] = threshold

    def set(
        self,
        threshold: AnomalyThreshold,
    ) -> None:
        """Create or replace a threshold."""
        self._thresholds[threshold.name] = threshold

    def get(
        self,
        name: str,
    ) -> AnomalyThreshold:
        """Return a threshold by name."""
        if not name.strip():
            raise ValueError("name must not be empty.")

        try:
            return self._thresholds[name]
        except KeyError as exc:
            raise KeyError(f"Threshold not found: {name}") from exc

    def remove(
        self,
        name: str,
    ) -> None:
        """Remove a threshold."""
        if not name.strip():
            raise ValueError("name must not be empty.")

        if name not in self._thresholds:
            raise KeyError(f"Threshold not found: {name}")

        del self._thresholds[name]

    def list_all(self) -> tuple[AnomalyThreshold, ...]:
        """Return all thresholds sorted by name."""
        return tuple(self._thresholds[name] for name in sorted(self._thresholds))

    def list_enabled(self) -> tuple[AnomalyThreshold, ...]:
        """Return enabled thresholds sorted by name."""
        return tuple(threshold for threshold in self.list_all() if threshold.enabled)

    def contains(
        self,
        name: str,
    ) -> bool:
        """Return whether a threshold exists."""
        return name in self._thresholds

    def clear(self) -> None:
        """Remove all registered thresholds."""
        self._thresholds.clear()

    @property
    def count(self) -> int:
        """Return number of registered thresholds."""
        return len(self._thresholds)
