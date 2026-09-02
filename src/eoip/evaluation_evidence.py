"""Evidence-safe analytical evaluation artifacts for EOIP Phase K."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class EvaluationStatus(StrEnum):
    """Allowed success-criteria classifications."""

    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    NOT_VERIFIED = "NOT VERIFIED"
    NOT_APPLICABLE = "NOT APPLICABLE"


class ThresholdComparison(StrEnum):
    """Supported unambiguous numerical threshold comparisons."""

    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    ABSOLUTE_LESS_THAN_OR_EQUAL = "abs<="


def classify_numeric_threshold(
    *,
    actual: float | None,
    target: float,
    comparison: ThresholdComparison,
) -> EvaluationStatus:
    """Classify a metric without converting unavailable evidence to PASS."""
    if actual is None:
        return EvaluationStatus.NOT_VERIFIED
    if comparison is ThresholdComparison.GREATER_THAN_OR_EQUAL:
        passed = actual >= target
    elif comparison is ThresholdComparison.LESS_THAN:
        passed = actual < target
    else:
        passed = abs(actual) <= target
    return EvaluationStatus.PASS if passed else EvaluationStatus.FAIL


@dataclass(frozen=True, slots=True)
class CriterionEvidence:
    """One threshold comparison with an explicit evidence statement."""

    criterion: str
    metric: str
    target: str
    actual: float | int | str | None
    status: EvaluationStatus
    evidence: str
    notes: str = ""

    def __post_init__(self) -> None:
        """Reject ambiguous or empty evidence records."""
        for name in ("criterion", "metric", "target", "evidence"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
        if self.actual is None and self.status is EvaluationStatus.PASS:
            raise ValueError("A criterion without an actual value cannot PASS.")


@dataclass(frozen=True, slots=True)
class EvaluationArtifact:
    """Versioned, machine-readable evaluation evidence."""

    schema_version: str
    area: str
    model_name: str
    model_version: str
    dataset: str | None
    evaluation_period: str | None
    evaluated_at: datetime
    criteria: tuple[CriterionEvidence, ...]
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate artifact identity and timestamp semantics."""
        for name in ("schema_version", "area", "model_name", "model_version"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware.")
        if not self.criteria:
            raise ValueError("criteria must not be empty.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe mapping."""
        payload = asdict(self)
        payload["evaluated_at"] = self.evaluated_at.isoformat()
        for criterion in payload["criteria"]:
            criterion["status"] = criterion["status"].value
        return payload


def write_evaluation_artifact(
    artifact: EvaluationArtifact,
    destination: Path,
) -> Path:
    """Write an artifact atomically as stable, indented JSON."""
    if destination.suffix.casefold() != ".json":
        raise ValueError("Evaluation artifacts must use a .json extension.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(artifact.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


__all__ = [
    "CriterionEvidence",
    "EvaluationArtifact",
    "EvaluationStatus",
    "ThresholdComparison",
    "classify_numeric_threshold",
    "write_evaluation_artifact",
]
