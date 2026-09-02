"""Generate Phase K capability artifacts without inventing model results."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from eoip.evaluation_evidence import (
    CriterionEvidence,
    EvaluationArtifact,
    EvaluationStatus,
    write_evaluation_artifact,
)


def _criterion(
    name: str,
    metric: str,
    target: str,
    *,
    status: EvaluationStatus,
    evidence: str,
    actual: float | int | str | None = None,
    notes: str = "",
) -> CriterionEvidence:
    return CriterionEvidence(name, metric, target, actual, status, evidence, notes)


def build_capability_artifacts(
    evaluated_at: datetime,
) -> tuple[EvaluationArtifact, ...]:
    """Return honest artifacts describing what can be evaluated now."""
    unavailable = "No repository evaluation dataset/model run was available."
    return (
        EvaluationArtifact(
            "1.0",
            "forecasting",
            "candidate forecast model",
            "unavailable",
            None,
            None,
            evaluated_at,
            (
                _criterion(
                    "MAE improvement",
                    "mae_improvement_percent",
                    ">= 10%",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "WAPE improvement",
                    "wape_improvement_percent",
                    ">= 10%",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "RMSE improvement",
                    "rmse_improvement_percent",
                    ">= 10%",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "Forecast bias",
                    "bias_percent",
                    "absolute value <= 5%",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "Prediction interval coverage",
                    "coverage_percent",
                    ">= 90%",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
            ),
            {"baseline": "Seasonal Naive", "implementation_ready": True},
        ),
        EvaluationArtifact(
            "1.0",
            "anomaly_detection",
            "anomaly detector",
            "unavailable",
            None,
            None,
            evaluated_at,
            (
                _criterion(
                    "Critical recall",
                    "critical_recall",
                    ">= 0.95",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "Precision",
                    "precision",
                    ">= 0.90",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "F1",
                    "f1",
                    ">= 0.90",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "False alerts",
                    "false_alerts_per_asset_day",
                    "< 0.20",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "Detection delay",
                    "detection_delay_minutes",
                    "< 15 minutes",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
            ),
            {"ground_truth_required": True, "explicit_asset_exposure_required": True},
        ),
        EvaluationArtifact(
            "1.0",
            "predictive_maintenance",
            "failure prediction model",
            "unavailable",
            None,
            None,
            evaluated_at,
            (
                _criterion(
                    "PR-AUC",
                    "pr_auc",
                    ">= 0.80",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "ROC-AUC",
                    "roc_auc",
                    ">= 0.90",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "Top-5%-risk recall",
                    "top_five_percent_recall",
                    ">= 0.85",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "Precision",
                    "precision",
                    ">= 0.80",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
                _criterion(
                    "Calibration evaluated",
                    "brier_score",
                    "evaluation required; no quality threshold defined",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence=unavailable,
                ),
            ),
            {"calibration_bins": 10, "top_risk_rounding": "ceil(n * 0.05), minimum 1"},
        ),
        EvaluationArtifact(
            "1.0",
            "equipment_health",
            "weighted degradation score",
            "1.0",
            None,
            None,
            evaluated_at,
            (
                _criterion(
                    "Component breakdown",
                    "weighted_component_contributions",
                    "available",
                    status=EvaluationStatus.PASS,
                    actual="available",
                    evidence=(
                        "Five model inputs are multiplied by their declared weights "
                        "and sum to degradation_score."
                    ),
                ),
                _criterion(
                    "Confidence",
                    "health_confidence",
                    "available",
                    status=EvaluationStatus.FAIL,
                    actual="unsupported",
                    evidence=(
                        "No uncertainty, calibration, ensemble, or "
                        "sample-sufficiency model exists."
                    ),
                ),
                _criterion(
                    "Historical validation",
                    "historical_outcome_validation",
                    "completed",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence="Timestamped validation outcomes are unavailable.",
                ),
                _criterion(
                    "Ground-truth validation",
                    "health_ground_truth_validation",
                    "completed",
                    status=EvaluationStatus.NOT_VERIFIED,
                    evidence="No accepted health ground-truth label contract exists.",
                ),
            ),
            {
                "confidence_intentionally_not_derived_from": [
                    "health_score",
                    "failure_probability",
                ]
            },
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation"))
    parser.add_argument("--evaluated-at", type=datetime.fromisoformat)
    args = parser.parse_args()
    evaluated_at = args.evaluated_at or datetime.now(UTC)
    if evaluated_at.tzinfo is None:
        raise ValueError("--evaluated-at must include a UTC offset.")
    for artifact in build_capability_artifacts(evaluated_at):
        path = args.output / f"{artifact.area}_phase_k.json"
        write_evaluation_artifact(artifact, path)
        print(path.as_posix())


if __name__ == "__main__":
    main()
