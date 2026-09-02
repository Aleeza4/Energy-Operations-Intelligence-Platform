"""Tests for evidence-safe Phase K artifact contracts."""

import json
from datetime import UTC, datetime

import pytest

from eoip.evaluation_evidence import (
    CriterionEvidence,
    EvaluationArtifact,
    EvaluationStatus,
    ThresholdComparison,
    classify_numeric_threshold,
    write_evaluation_artifact,
)


def test_missing_actual_cannot_pass() -> None:
    with pytest.raises(ValueError, match="cannot PASS"):
        CriterionEvidence(
            "Metric", "metric", ">= 1", None, EvaluationStatus.PASS, "none"
        )


@pytest.mark.parametrize(
    ("actual", "target", "comparison", "expected"),
    [
        (10.0, 10.0, ThresholdComparison.GREATER_THAN_OR_EQUAL, EvaluationStatus.PASS),
        (9.99, 10.0, ThresholdComparison.GREATER_THAN_OR_EQUAL, EvaluationStatus.FAIL),
        (0.19, 0.20, ThresholdComparison.LESS_THAN, EvaluationStatus.PASS),
        (0.20, 0.20, ThresholdComparison.LESS_THAN, EvaluationStatus.FAIL),
        (
            5.0,
            5.0,
            ThresholdComparison.ABSOLUTE_LESS_THAN_OR_EQUAL,
            EvaluationStatus.PASS,
        ),
        (
            -5.01,
            5.0,
            ThresholdComparison.ABSOLUTE_LESS_THAN_OR_EQUAL,
            EvaluationStatus.FAIL,
        ),
        (
            None,
            10.0,
            ThresholdComparison.GREATER_THAN_OR_EQUAL,
            EvaluationStatus.NOT_VERIFIED,
        ),
    ],
)
def test_numeric_threshold_boundaries(actual, target, comparison, expected) -> None:
    assert (
        classify_numeric_threshold(actual=actual, target=target, comparison=comparison)
        is expected
    )


def test_artifact_serialization_preserves_null_and_status(tmp_path) -> None:
    artifact = EvaluationArtifact(
        "1.0",
        "forecasting",
        "model",
        "1",
        None,
        None,
        datetime(2026, 8, 26, tzinfo=UTC),
        (
            CriterionEvidence(
                "WAPE", "wape", ">= 10%", None, EvaluationStatus.NOT_VERIFIED, "No run."
            ),
        ),
        {},
    )
    path = write_evaluation_artifact(artifact, tmp_path / "artifact.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["criteria"][0]["actual"] is None
    assert payload["criteria"][0]["status"] == "NOT VERIFIED"
