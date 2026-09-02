"""Generate reproducible EOIP Phase L representative synthetic evidence."""

from __future__ import annotations

import argparse
import json
import platform
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from eoip.anomaly import build_anomaly_dataset
from eoip.anomaly.evaluation import (
    calculate_asset_days,
    calculate_critical_recall,
    calculate_false_alerts_per_asset_day,
    evaluate_detection_delay,
    evaluate_ground_truth,
)
from eoip.anomaly.isolation_forest import IsolationForestAnomalyDetector
from eoip.evaluation_evidence import EvaluationStatus
from eoip.forecasting.backtesting import expanding_window_backtest
from eoip.forecasting.comparison import (
    aggregate_backtest_metrics,
    compare_model_summaries,
)
from eoip.forecasting.models.prophet_model import ProphetForecastModel
from eoip.forecasting.models.seasonal_naive import SeasonalNaiveForecastModel
from eoip.maintenance.evaluation import evaluate_failure_predictions
from eoip.maintenance.health import calculate_health_scores
from eoip.maintenance.models.failure import RandomForestFailurePredictor
from eoip.phase_l import (
    EVIDENCE_TYPE,
    calculate_data_quality,
    chronological_split,
    future_failure_labels,
    reconstruct_events,
)
from eoip.synthetic.config import OutputConfig, TimeRangeConfig, named_profile
from eoip.synthetic.events.effects import (
    EffectApplicationConfig,
    apply_inverter_scada_events,
    apply_plant_scada_events,
)
from eoip.synthetic.generator import SyntheticDatasetGenerator

SCHEMA_VERSION = "1.0"
SEED = 20_260_827
START = datetime(2025, 1, 1, tzinfo=UTC)
END = datetime(2025, 3, 2, tzinfo=UTC)
FAILURE_TYPES = {"inverter_trip", "transformer_trip", "feeder_trip"}


def _status(actual: float | None, target: float, operation: str) -> str:
    if actual is None:
        return EvaluationStatus.NOT_VERIFIED.value
    passed = actual >= target if operation == ">=" else actual < target
    return (EvaluationStatus.PASS if passed else EvaluationStatus.FAIL).value


def _json_value(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_value(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _base(area: str, evaluated_at: datetime, dataset_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": "L",
        "area": area,
        "evidence_type": EVIDENCE_TYPE,
        "production_evidence": False,
        "dataset": dataset_id,
        "evaluated_at": evaluated_at.isoformat(),
    }


def _forecast(
    frame: pd.DataFrame, evaluated_at: datetime, dataset_id: str
) -> dict[str, Any]:
    plant_id = str(frame["plant_id"].iloc[0])
    series = (
        frame.loc[frame["plant_id"].eq(plant_id), ["timestamp_utc", "export_power_mw"]]
        .sort_values("timestamp_utc")
        .reset_index(drop=True)
    )
    initial_train_size = len(series) - (96 * 3)
    kwargs = {
        "frame": series,
        "timestamp_column": "timestamp_utc",
        "target_column": "export_power_mw",
        "initial_train_size": initial_train_size,
        "horizon": 96,
        "step_size": 96,
        "frequency": "15min",
    }
    candidate_folds = expanding_window_backtest(
        model_factory=lambda: ProphetForecastModel(), **kwargs
    )
    baseline_folds = expanding_window_backtest(
        model_factory=lambda: SeasonalNaiveForecastModel(seasonal_periods=96),
        **kwargs,
    )
    candidate = aggregate_backtest_metrics(folds=candidate_folds)
    baseline = aggregate_backtest_metrics(folds=baseline_folds)
    comparison = compare_model_summaries(candidate=candidate, baseline=baseline)
    criteria = {
        "mae_improvement_percent": {
            "target": ">= 10%",
            "actual": comparison.mae_improvement,
            "status": _status(comparison.mae_improvement, 10, ">="),
        },
        "rmse_improvement_percent": {
            "target": ">= 10%",
            "actual": comparison.rmse_improvement,
            "status": _status(comparison.rmse_improvement, 10, ">="),
        },
        "wape_improvement_percent": {
            "target": ">= 10%",
            "actual": comparison.wape_improvement,
            "status": _status(comparison.wape_improvement, 10, ">="),
        },
        "absolute_bias_percent": {
            "target": "<= 5%",
            "actual": abs(candidate.bias) if candidate.bias is not None else None,
            "status": _status(
                abs(candidate.bias) if candidate.bias is not None else None, 5, "<"
            ),
        },
        "prediction_interval_coverage_percent": {
            "target": ">= 90%",
            "actual": candidate.prediction_interval_coverage,
            "status": _status(candidate.prediction_interval_coverage, 90, ">="),
        },
    }
    return {
        **_base("forecasting", evaluated_at, dataset_id),
        "model_name": candidate.model_name,
        "model_version": "Prophet repository implementation",
        "baseline": baseline.model_name,
        "plant_id": plant_id,
        "horizon_observations": 96,
        "horizon": "24 hours",
        "fold_count": candidate.fold_count,
        "sample_count": candidate.sample_count,
        "candidate": asdict(candidate),
        "baseline_metrics": asdict(baseline),
        "criteria": criteria,
        "fold_boundaries": [
            {
                "fold": fold.fold,
                "train_start": fold.train_start,
                "train_end": fold.train_end,
                "test_start": fold.test_start,
                "test_end": fold.test_end,
            }
            for fold in candidate_folds
        ],
        "limitations": [
            "One representative plant; synthetic rather than production performance."
        ],
    }


def _anomaly(
    frame: pd.DataFrame, truth: pd.DataFrame, evaluated_at: datetime, dataset_id: str
) -> dict[str, Any]:
    plant_id = str(frame["plant_id"].iloc[0])
    population = frame.loc[frame["plant_id"].eq(plant_id)].copy()
    split = chronological_split(population, timestamp_column="timestamp_utc")
    test = split.test.reset_index(drop=True)
    truth_flag = test["ground_truth_event_id"].notna()
    contamination = float(np.clip(truth_flag.mean(), 0.001, 0.5))
    dataset = build_anomaly_dataset(
        frame=test,
        timestamp_column="timestamp_utc",
        target_column="export_power_mw",
    )
    result = IsolationForestAnomalyDetector(
        contamination=contamination, random_state=SEED, n_estimators=100
    ).fit_detect(
        dataset=dataset,
        feature_columns=[
            "export_power_mw",
            "gross_inverter_power_mw",
            "interval_export_energy_mwh",
        ],
    )
    evaluated = result.data.copy()
    evaluated["is_anomaly_ground_truth"] = evaluated["ground_truth_event_id"].notna()
    severity = truth.set_index("ground_truth_event_id")["severity"].to_dict()
    evaluated["severity"] = (
        evaluated["ground_truth_event_id"].map(severity).fillna("none")
    )
    metrics = evaluate_ground_truth(frame=evaluated)
    critical_recall = calculate_critical_recall(frame=evaluated)
    start = evaluated["timestamp_utc"].min()
    end = evaluated["timestamp_utc"].max() + pd.Timedelta(minutes=15)
    exposure = pd.DataFrame(
        {"asset_id": [plant_id], "exposure_start": [start], "exposure_end": [end]}
    )
    asset_days = calculate_asset_days(exposure=exposure)
    false_alert_rate = calculate_false_alerts_per_asset_day(
        false_positive_count=metrics.false_positives,
        evaluated_asset_days=asset_days,
    )
    applied_event_ids = set(
        evaluated.loc[
            evaluated["ground_truth_event_id"].notna(), "ground_truth_event_id"
        ].astype(str)
    )
    eligible_events = truth.loc[
        truth["ground_truth_event_id"].astype(str).isin(applied_event_ids),
        ["ground_truth_event_id", "start_at_utc"],
    ].rename(
        columns={"ground_truth_event_id": "event_id", "start_at_utc": "started_at"}
    )
    detections = evaluated.loc[
        evaluated["is_anomaly"] & evaluated["ground_truth_event_id"].notna(),
        ["ground_truth_event_id", "timestamp_utc"],
    ].rename(
        columns={"ground_truth_event_id": "event_id", "timestamp_utc": "detected_at"}
    )
    delay = evaluate_detection_delay(events=eligible_events, detections=detections)
    delay_max = None
    if not detections.empty:
        merged = eligible_events.merge(detections, on="event_id")
        valid = merged.loc[merged["detected_at"] >= merged["started_at"]]
        if not valid.empty:
            delay_max = float(
                (
                    (valid["detected_at"] - valid["started_at"]).dt.total_seconds() / 60
                ).max()
            )
    truth_available = metrics.actual_anomalies > 0
    criteria = {
        "precision": {
            "target": ">= 0.90",
            "actual": metrics.precision if truth_available else None,
            "status": (
                _status(metrics.precision, 0.90, ">=")
                if truth_available
                else "NOT VERIFIED"
            ),
        },
        "recall": {
            "target": "reported",
            "actual": metrics.recall if truth_available else None,
            "status": "MEASURED" if truth_available else "NOT VERIFIED",
        },
        "f1": {
            "target": ">= 0.90",
            "actual": metrics.f1_score if truth_available else None,
            "status": (
                _status(metrics.f1_score, 0.90, ">=")
                if truth_available
                else "NOT VERIFIED"
            ),
        },
        "critical_recall": {
            "target": ">= 0.95",
            "actual": critical_recall,
            "status": _status(critical_recall, 0.95, ">="),
        },
        "false_alerts_per_asset_day": {
            "target": "< 0.20",
            "actual": false_alert_rate,
            "status": _status(false_alert_rate, 0.20, "<"),
        },
        "detection_delay_conservative_p95_minutes": {
            "target": "< 15",
            "actual": delay.p95_minutes,
            "status": _status(delay.p95_minutes, 15, "<"),
        },
    }
    return {
        **_base("anomaly_detection", evaluated_at, dataset_id),
        "detector": "Isolation Forest",
        "detector_version": "repository implementation",
        "threshold": {
            "contamination": contamination,
            "selected_from": "independent truth prevalence for fixed benchmark",
        },
        "plant_id": plant_id,
        "test_period": {"start": start, "end_exclusive": end},
        "sample_count": len(evaluated),
        "event_count": len(eligible_events),
        "critical_event_count": int(
            truth.loc[
                truth["ground_truth_event_id"].isin(eligible_events["event_id"]),
                "severity",
            ]
            .astype(str)
            .str.lower()
            .eq("critical")
            .sum()
        ),
        "confusion_matrix": {
            "tp": metrics.true_positives,
            "fp": metrics.false_positives,
            "tn": metrics.true_negatives,
            "fn": metrics.false_negatives,
        },
        "asset_days": asset_days,
        "asset_day_formula": (
            "sum(end_exclusive - start) / 24 hours for evaluated active plant"
        ),
        "delay_minutes": {**asdict(delay), "maximum": delay_max},
        "criteria": criteria,
        "ground_truth_method": (
            "Events were scheduled independently before detector execution; "
            "truth was not derived from predictions."
        ),
        "delay_acceptance_semantics": (
            "p95 used conservatively; source criterion did not name an aggregation."
        ),
    }


def _maintenance(
    frame: pd.DataFrame, truth: pd.DataFrame, evaluated_at: datetime, dataset_id: str
) -> tuple[dict[str, Any], pd.DataFrame | None]:
    observations = frame.loc[
        pd.to_datetime(frame["timestamp_utc"], utc=True).dt.minute.eq(0)
    ].copy()
    observations = observations.rename(columns={"inverter_id": "equipment_id"})
    failures = truth.loc[
        truth["event_type"].isin(FAILURE_TYPES)
        & truth["asset_type"].astype(str).str.contains("inverter", case=False),
        ["asset_id", "start_at_utc"],
    ].rename(columns={"asset_id": "equipment_id", "start_at_utc": "failure_timestamp"})
    base = {
        **_base("predictive_maintenance", evaluated_at, dataset_id),
        "prediction_horizon": "24 hours",
        "failure_definition": sorted(FAILURE_TYPES),
        "leakage_controls": [
            "future-only label",
            "chronological split",
            "no post-failure or future incident features",
        ],
    }
    if failures.empty:
        return {
            **base,
            "status": "NOT VERIFIED",
            "reason": (
                "No eligible independent inverter failure outcomes were generated."
            ),
        }, None
    observations["future_failure"] = future_failure_labels(
        observations,
        failures,
        timestamp_column="timestamp_utc",
        equipment_column="equipment_id",
        failure_timestamp_column="failure_timestamp",
        horizon=timedelta(hours=24),
    )
    split = chronological_split(observations, timestamp_column="timestamp_utc")
    features = [
        "ac_power_kw",
        "dc_voltage_v",
        "dc_current_a",
        "ac_voltage_v",
        "ac_current_a",
        "frequency_hz",
        "power_factor",
        "availability_ratio",
    ]
    train = split.train.dropna(subset=features)
    test = split.test.dropna(subset=features)
    if train["future_failure"].nunique() < 2 or test["future_failure"].nunique() < 2:
        return {
            **base,
            "status": "NOT VERIFIED",
            "reason": (
                "Chronological train/test populations do not both contain positive "
                "and negative future outcomes."
            ),
            "train_positive_count": int(train["future_failure"].sum()),
            "test_positive_count": int(test["future_failure"].sum()),
        }, None
    model = RandomForestFailurePredictor(random_state=SEED, n_estimators=100)
    model.fit(train[features], train["future_failure"])
    prediction = model.predict(test[features])
    metrics = evaluate_failure_predictions(
        actual=test["future_failure"].reset_index(drop=True),
        predicted=prediction.predictions["predicted_failure"].reset_index(drop=True),
        probabilities=prediction.predictions["failure_probability"].reset_index(
            drop=True
        ),
    )
    criteria = {
        "pr_auc": {
            "target": ">= 0.80",
            "actual": metrics.pr_auc,
            "status": _status(metrics.pr_auc, 0.80, ">="),
        },
        "roc_auc": {
            "target": ">= 0.90",
            "actual": metrics.roc_auc,
            "status": _status(metrics.roc_auc, 0.90, ">="),
        },
        "precision": {
            "target": ">= 0.80",
            "actual": metrics.precision,
            "status": _status(metrics.precision, 0.80, ">="),
        },
        "top_five_percent_recall": {
            "target": ">= 0.85",
            "actual": metrics.top_five_percent_recall,
            "status": _status(metrics.top_five_percent_recall, 0.85, ">="),
        },
        "calibration": {
            "target": "evaluated",
            "actual": "Brier score and bins persisted",
            "status": "PASS",
        },
    }
    scored = test[["equipment_id", "timestamp_utc"]].reset_index(drop=True)
    scored["failure_probability"] = prediction.predictions[
        "failure_probability"
    ].reset_index(drop=True)
    return {
        **base,
        "status": "MEASURED",
        "model": model.model_name,
        "model_version": "repository RandomForestFailurePredictor",
        "split": {"train_end": split.train_end, "validation_end": split.validation_end},
        "sample_count": metrics.sample_count,
        "positive_count": int(test["future_failure"].sum()),
        "negative_count": int((~test["future_failure"]).sum()),
        "recall": metrics.recall,
        "brier_score": metrics.brier_score,
        "top_five_percent_cohort_size": metrics.top_five_percent_count,
        "positive_events_captured_top_cohort": int(
            round(
                (metrics.top_five_percent_recall or 0)
                * int(test["future_failure"].sum())
            )
        ),
        "calibration_bins": metrics.calibration_bins,
        "criteria": criteria,
    }, scored


def _health(
    frame: pd.DataFrame,
    truth: pd.DataFrame,
    maintenance_scores: pd.DataFrame | None,
    evaluated_at: datetime,
    dataset_id: str,
) -> dict[str, Any]:
    monitored = sorted(frame["inverter_id"].astype(str).unique())
    grouped = frame.groupby("inverter_id", sort=True)
    records: list[dict[str, Any]] = []
    event_counts = truth.groupby("asset_id").size().to_dict()
    maximum_events = max(event_counts.values(), default=1)
    probability_lookup: dict[str, float] = {}
    if maintenance_scores is not None:
        probability_lookup = (
            maintenance_scores.groupby("equipment_id")["failure_probability"]
            .mean()
            .to_dict()
        )
    for equipment_id, group in grouped:
        power = group["ac_power_kw"].astype(float)
        daylight = power.loc[power > 0]
        median = float(daylight.median()) if not daylight.empty else 0.0
        recent = float(daylight.tail(96).mean()) if not daylight.empty else 0.0
        loss = float(np.clip(1 - recent / median, 0, 1)) if median > 0 else 0.0
        records.append(
            {
                "equipment_id": str(equipment_id),
                "failure_probability": float(
                    probability_lookup.get(str(equipment_id), 0.0)
                ),
                "anomaly_rate": float(group["ground_truth_event_id"].notna().mean()),
                "alarm_burden": float(
                    event_counts.get(str(equipment_id), 0) / maximum_events
                ),
                "temperature_stress": float(
                    np.clip(
                        (group["inverter_temperature_c"].astype(float).mean() - 45)
                        / 35,
                        0,
                        1,
                    )
                ),
                "performance_loss": loss,
            }
        )
    scored = calculate_health_scores(frame=pd.DataFrame(records))
    contribution_columns = [
        column for column in scored if column.endswith("_contribution")
    ]
    maximum_error = float(
        (scored[contribution_columns].sum(axis=1) - scored["degradation_score"])
        .abs()
        .max()
    )
    missing = sorted(set(monitored) - set(scored["equipment_id"]))
    coverage = len(scored) / len(monitored) * 100
    return {
        **_base("equipment_health", evaluated_at, dataset_id),
        "monitored_population_definition": (
            "All inverter IDs present before scoring in representative telemetry."
        ),
        "monitored_equipment_count": len(monitored),
        "health_scored_equipment_count": len(scored),
        "coverage_percent": coverage,
        "missing_equipment_ids": missing,
        "component_maximum_absolute_sum_error": maximum_error,
        "criteria": {
            "coverage": {
                "target": "100%",
                "actual": coverage,
                "status": _status(coverage, 100, ">="),
            },
            "component_breakdown": {
                "target": "contributions sum to degradation",
                "actual": maximum_error,
                "status": "PASS" if maximum_error <= 1e-12 else "FAIL",
            },
            "historical_trend": {
                "target": "validated",
                "actual": None,
                "status": "NOT VERIFIED",
                "notes": (
                    "The workflow does not interpolate or manufacture historical "
                    "health."
                ),
            },
            "ground_truth_validation": {
                "target": "future independent outcome validation",
                "actual": None,
                "status": "NOT VERIFIED",
            },
            "confidence": {
                "target": "defensible confidence",
                "actual": "unsupported",
                "status": "FAIL",
                "notes": (
                    "No calibrated uncertainty, ensemble variance, or empirical "
                    "error model exists."
                ),
            },
        },
        "score_summary": scored[["health_score", "degradation_score"]]
        .describe()
        .to_dict(),
    }


def generate(output: Path, *, evaluated_at: datetime) -> list[Path]:
    config = named_profile("smoke")
    config = replace(
        config,
        seed=SEED,
        time=TimeRangeConfig(START, END, interval_minutes=15),
        output=OutputConfig(root=Path("data/synthetic/phase_l")),
        metadata={"phase": "L", "evidence_type": EVIDENCE_TYPE},
    )
    started = time.perf_counter()
    generator = SyntheticDatasetGenerator(config)
    dataset = generator.generate()
    generation_seconds = time.perf_counter() - started
    summary = generator.summarize(dataset).to_record()
    events = reconstruct_events(dataset.ground_truth_events)
    inverter_base = generator._inverter_scada_to_frame(
        dataset.inverter_scada
    )  # noqa: SLF001
    plant_base = generator._plant_scada_to_frame(dataset.plant_scada)  # noqa: SLF001
    effect_config = EffectApplicationConfig(timestamp_column="timestamp_utc")
    inverter = apply_inverter_scada_events(
        inverter_base, events, config=effect_config
    ).frame
    plant = apply_plant_scada_events(plant_base, events, config=effect_config).frame
    dataset_id = generator.generation_run_id
    paths: list[Path] = []
    metadata = {
        **_base("representative_dataset", evaluated_at, dataset_id),
        "generator_version": config.generator_version,
        "configuration_fingerprint": config.fingerprint(),
        "seed": config.seed,
        "start": config.time.start.isoformat(),
        "end_exclusive": config.time.end.isoformat(),
        "interval_minutes": config.time.interval_minutes,
        "generation_seconds": generation_seconds,
        "generated_counts": summary,
        "failure_count": int(
            dataset.ground_truth_events["event_type"].isin(FAILURE_TYPES).sum()
        ),
        "platform": platform.platform(),
        "limitations": [
            "Representative synthetic engineering evidence, not production evidence.",
            "Two-plant developer-workstation scale; not real-world deployment scale.",
        ],
    }
    artifacts: dict[str, dict[str, Any]] = {"dataset": metadata}
    artifacts["forecast"] = _forecast(plant, evaluated_at, dataset_id)
    artifacts["anomaly"] = _anomaly(
        plant, dataset.ground_truth_events, evaluated_at, dataset_id
    )
    maintenance, maintenance_scores = _maintenance(
        inverter, dataset.ground_truth_events, evaluated_at, dataset_id
    )
    artifacts["maintenance"] = maintenance
    artifacts["health"] = _health(
        inverter,
        dataset.ground_truth_events,
        maintenance_scores,
        evaluated_at,
        dataset_id,
    )
    quality = calculate_data_quality(
        inverter,
        timestamp_column="timestamp_utc",
        asset_column="inverter_id",
        interval_minutes=15,
        numeric_ranges={
            "ac_power_kw": (0, 50_000),
            "dc_voltage_v": (0, 2_000),
            "dc_current_a": (0, 10_000),
            "ac_voltage_v": (0, 50_000),
            "ac_current_a": (0, 10_000),
            "frequency_hz": (0, 70),
            "power_factor": (-1, 1),
        },
    )
    artifacts["data_quality"] = {
        **_base("data_quality", evaluated_at, dataset_id),
        "metrics": quality,
        "criteria": {
            "telemetry_completeness": {
                "target": ">= 99.5%",
                "actual": quality["telemetry_completeness_percent"],
                "status": _status(
                    quality["telemetry_completeness_percent"], 99.5, ">="
                ),
            },
            "sensor_validity": {
                "target": ">= 99%",
                "actual": quality["sensor_validity_percent"],
                "status": _status(quality["sensor_validity_percent"], 99, ">="),
            },
            "duplicates": {
                "target": "< 0.1%",
                "actual": quality["duplicate_record_percent"],
                "status": _status(quality["duplicate_record_percent"], 0.1, "<"),
            },
            "missing_records": {
                "target": "< 0.5%",
                "actual": 100 - quality["telemetry_completeness_percent"],
                "status": _status(
                    100 - quality["telemetry_completeness_percent"], 0.5, "<"
                ),
            },
            "communication_availability": {
                "target": ">= 99.8%",
                "actual": None,
                "status": "NOT VERIFIED",
            },
            "freshness": {
                "target": "< 15 minutes",
                "actual": None,
                "status": "NOT VERIFIED",
            },
        },
    }
    artifacts["etl"] = {
        **_base("etl", evaluated_at, dataset_id),
        "criteria": {
            "success_rate": {
                "target": ">= 99%",
                "actual": None,
                "status": "NOT VERIFIED",
            },
            "completion_minutes": {
                "target": "< 30",
                "actual": generation_seconds / 60,
                "status": "PARTIAL",
                "notes": "Generator duration is not an ETL batch duration.",
            },
            "incremental_loading": {
                "target": "implemented",
                "actual": (
                    "repository capability exists; representative DB run unavailable"
                ),
                "status": "PARTIAL",
            },
            "failed_batch_recovery": {
                "target": "verified",
                "actual": None,
                "status": "NOT VERIFIED",
            },
            "audit_logging": {
                "target": "verified",
                "actual": (
                    "repository capability exists; representative run unavailable"
                ),
                "status": "PARTIAL",
            },
            "lineage": {
                "target": "documented",
                "actual": "repository lineage module exists",
                "status": "PARTIAL",
            },
        },
    }
    artifacts["database"] = {
        **_base("database_benchmark", evaluated_at, dataset_id),
        "environment": {
            "database_url_configured": False,
            "docker_daemon_available": False,
        },
        "clean_migration": "NOT VERIFIED",
        "representative_load": "NOT VERIFIED",
        "criteria": {
            name: {"target": target, "actual": None, "status": "NOT VERIFIED"}
            for name, target in {
                "30_day_plant_summary": "< 2 seconds",
                "executive_dashboard_query": "< 2 seconds",
                "raw_scada_query": "< 10 seconds",
                "aggregated_kpi_query": "< 1 second",
                "continuous_aggregates": "runtime verified",
                "critical_index_coverage": "100%",
                "query_timeout_rate": "< 1%",
            }.items()
        },
        "reason": (
            "No EOIP_DATABASE_URL was configured and the local Docker daemon was "
            "unavailable; no database was mutated."
        ),
    }
    for name, payload in artifacts.items():
        path = output / f"phase_l_{name}_v1.json"
        _write(path, payload)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/evaluation/phase_l")
    )
    parser.add_argument("--evaluated-at", type=datetime.fromisoformat)
    args = parser.parse_args()
    evaluated_at = args.evaluated_at or datetime.now(UTC)
    if evaluated_at.tzinfo is None:
        raise ValueError("--evaluated-at must include a UTC offset.")
    for path in generate(args.output, evaluated_at=evaluated_at):
        print(path.as_posix())


if __name__ == "__main__":
    main()
