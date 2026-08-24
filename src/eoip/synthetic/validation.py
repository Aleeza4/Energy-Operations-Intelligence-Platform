"""Comprehensive in-memory Phase 2 validation layer for synthetic datasets.

This module validates a fully assembled :class:`SyntheticDataset` after
``generator.py`` has produced it and before any output pipeline publishes it.

Validation is read-only. It never mutates the dataset, its tuples, model
objects, or DataFrames.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np
import pandas as pd

from eoip.synthetic.config import GenerationConfig, ValidationConfig
from eoip.synthetic.generator import SyntheticDataset
from eoip.synthetic.models.equipment import Equipment
from eoip.synthetic.models.meter import RevenueMeter
from eoip.synthetic.models.plant import Plant
from eoip.synthetic.models.plant_scada import PlantSCADAObservation
from eoip.synthetic.models.scada import SCADAObservation
from eoip.synthetic.models.weather import WeatherObservation


class ValidationSeverity(StrEnum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One detected data-quality or invariant violation."""

    rule_id: str
    severity: ValidationSeverity
    dataset: str
    message: str
    identifier: str | None = None
    sample_records: tuple[Any, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "dataset": self.dataset,
            "message": self.message,
            "identifier": self.identifier,
            "sample_records": list(self.sample_records),
        }


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Aggregated outcome of validating one dataset."""

    rule_id: str
    dataset: str
    severity: ValidationSeverity
    passed: bool
    checked_count: int
    failed_count: int
    message: str
    sample_keys: tuple[Any, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "rule_id": self.rule_id,
            "dataset": self.dataset,
            "severity": self.severity.value,
            "passed": self.passed,
            "checked_count": self.checked_count,
            "failed_count": self.failed_count,
            "message": self.message,
            "sample_keys": list(self.sample_keys),
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Complete validation report for one generation run."""

    config: ValidationConfig
    results: tuple[ValidationResult, ...] = field(default_factory=tuple)
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        """Return whether validation passed publication rules."""
        error_count = sum(
            1 for issue in self.issues if issue.severity is ValidationSeverity.ERROR
        )
        warning_count = sum(
            1 for issue in self.issues if issue.severity is ValidationSeverity.WARNING
        )
        if error_count > 0:
            return False
        return not (self.config.fail_on_warning and warning_count > 0)

    @property
    def error_count(self) -> int:
        """Return the number of error issues."""
        return sum(
            1 for issue in self.issues if issue.severity is ValidationSeverity.ERROR
        )

    @property
    def warning_count(self) -> int:
        """Return the number of warning issues."""
        return sum(
            1 for issue in self.issues if issue.severity is ValidationSeverity.WARNING
        )

    @property
    def issue_count(self) -> int:
        """Return the total number of issues."""
        return len(self.issues)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable report summary."""
        return {
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issue_count": self.issue_count,
            "results": [result.to_dict() for result in self.results],
            "issues": [issue.to_dict() for issue in self.issues],
        }


class SyntheticDatasetValidator:
    """Read-only validator for fully assembled synthetic datasets.

    The validator inspects a :class:`SyntheticDataset` produced by
    :class:`eoip.synthetic.generator.SyntheticDatasetGenerator` and returns a
    :class:`ValidationReport`. It never mutates its inputs.
    """

    def __init__(self, config: GenerationConfig) -> None:
        """Initialize the validator with a generation configuration."""
        if not isinstance(config, GenerationConfig):
            raise TypeError("config must be a GenerationConfig.")
        self._config = config
        self._validation_config = config.validation

    def validate_dataset(self, dataset: SyntheticDataset) -> ValidationReport:
        """Validate a complete synthetic dataset and return a report.

        Parameters
        ----------
        dataset:
            Fully assembled dataset produced by the generator.

        Returns
        -------
        ValidationReport
            Collected validation results and issues.
        """
        if not isinstance(dataset, SyntheticDataset):
            raise TypeError("dataset must be a SyntheticDataset.")

        results: list[ValidationResult] = []
        issues: list[ValidationIssue] = []

        self._validate_structure(dataset, results, issues)
        self._validate_schema(dataset, results, issues)
        self._validate_identifiers(dataset, results, issues)
        self._validate_referential_integrity(dataset, results, issues)
        self._validate_temporal(dataset, results, issues)
        self._validate_volumes(dataset, results, issues)
        self._validate_numeric_physics(dataset, results, issues)
        self._validate_lifecycle(dataset, results, issues)

        return ValidationReport(
            config=self._validation_config,
            results=tuple(results),
            issues=tuple(issues),
        )

    def _record(
        self,
        rule_id: str,
        dataset: str,
        severity: ValidationSeverity,
        passed: bool,
        checked_count: int,
        failed_count: int,
        message: str,
        sample_keys: tuple[Any, ...] | None = None,
        results: list[ValidationResult] | None = None,
        issues: list[ValidationIssue] | None = None,
    ) -> None:
        """Append a rule result and optional issue."""
        result = ValidationResult(
            rule_id=rule_id,
            dataset=dataset,
            severity=severity,
            passed=passed,
            checked_count=checked_count,
            failed_count=failed_count,
            message=message,
            sample_keys=tuple(sample_keys or ())[
                : self._validation_config.maximum_failure_samples
            ],
        )
        if results is not None:
            results.append(result)
        if not passed and issues is not None:
            issues.append(
                ValidationIssue(
                    rule_id=rule_id,
                    severity=severity,
                    dataset=dataset,
                    message=message,
                    sample_records=tuple(result.sample_keys),
                )
            )

    def _validate_structure(
        self,
        dataset: SyntheticDataset,
        results: list[ValidationResult],
        issues: list[ValidationIssue],
    ) -> None:
        """Validate required datasets exist with expected container types."""
        checks = [
            ("plants", dataset.plants, tuple),
            ("equipment", dataset.equipment, tuple),
            ("revenue_meters", dataset.revenue_meters, tuple),
            ("weather", dataset.weather, tuple),
            ("inverter_scada", dataset.inverter_scada, tuple),
            ("plant_scada", dataset.plant_scada, tuple),
            ("ground_truth_events", dataset.ground_truth_events, pd.DataFrame),
            ("alarms", dataset.alarms, pd.DataFrame),
            ("incidents", dataset.incidents, pd.DataFrame),
            ("work_orders", dataset.work_orders, pd.DataFrame),
            ("tariffs", dataset.tariffs, pd.DataFrame),
            ("budgets", dataset.budgets, pd.DataFrame),
        ]
        for name, value, expected in checks:
            passed = isinstance(value, expected)
            self._record(
                rule_id="STR-001",
                dataset=name,
                severity=ValidationSeverity.ERROR,
                passed=passed,
                checked_count=1,
                failed_count=0 if passed else 1,
                message=(
                    f"{name} present as {expected.__name__}"
                    if passed
                    else f"{name} missing or wrong type"
                ),
                results=results,
                issues=issues,
            )

    def _validate_schema(
        self,
        dataset: SyntheticDataset,
        results: list[ValidationResult],
        issues: list[ValidationIssue],
    ) -> None:
        """Validate DataFrame columns and tuple-based model types."""
        frame_schemas = {
            "ground_truth_events": _GROUND_TRUTH_COLUMNS,
            "alarms": _ALARM_COLUMNS,
            "incidents": _INCIDENT_COLUMNS,
            "work_orders": _WORK_ORDER_COLUMNS,
            "tariffs": _TARIFF_COLUMNS,
            "budgets": _BUDGET_COLUMNS,
        }
        for name, expected in frame_schemas.items():
            frame = getattr(dataset, name)
            checked = len(frame.columns) if hasattr(frame, "columns") else 0
            missing = (
                sorted(set(expected).difference(frame.columns))
                if hasattr(frame, "columns")
                else list(expected)
            )
            failed = len(missing)
            passed = failed == 0
            self._record(
                rule_id="SCH-001",
                dataset=name,
                severity=ValidationSeverity.ERROR,
                passed=passed,
                checked_count=checked,
                failed_count=failed,
                message=(
                    f"missing columns: {missing}"
                    if not passed
                    else "schema columns present"
                ),
                sample_keys=tuple(
                    missing[: self._validation_config.maximum_failure_samples]
                ),
                results=results,
                issues=issues,
            )

        tuple_checks = [
            ("plants", dataset.plants, Plant),
            ("equipment", dataset.equipment, Equipment),
            ("revenue_meters", dataset.revenue_meters, RevenueMeter),
            ("weather", dataset.weather, WeatherObservation),
            ("inverter_scada", dataset.inverter_scada, SCADAObservation),
            ("plant_scada", dataset.plant_scada, PlantSCADAObservation),
        ]
        for name, values, expected_type in tuple_checks:
            bad = [
                i
                for i, value in enumerate(values)
                if not isinstance(value, expected_type)
            ]
            checked = len(values)
            failed = len(bad)
            passed = failed == 0
            self._record(
                rule_id="SCH-002",
                dataset=name,
                severity=ValidationSeverity.ERROR,
                passed=passed,
                checked_count=checked,
                failed_count=failed,
                message=(
                    "all records have expected model type"
                    if passed
                    else f"wrong model type at indices {bad[:5]}"
                ),
                sample_keys=tuple(
                    bad[: self._validation_config.maximum_failure_samples]
                ),
                results=results,
                issues=issues,
            )

    def _validate_identifiers(
        self,
        dataset: SyntheticDataset,
        results: list[ValidationResult],
        issues: list[ValidationIssue],
    ) -> None:
        """Validate primary-key uniqueness for key datasets."""
        plant_ids = [plant.plant_id for plant in dataset.plants]
        self._record(
            rule_id="ID-001",
            dataset="plants",
            severity=ValidationSeverity.ERROR,
            passed=len(plant_ids) == len(set(plant_ids)),
            checked_count=len(plant_ids),
            failed_count=len(plant_ids) - len(set(plant_ids)),
            message="plant IDs unique",
            sample_keys=tuple(pid for pid in plant_ids if plant_ids.count(pid) > 1)[
                : self._validation_config.maximum_failure_samples
            ],
            results=results,
            issues=issues,
        )

        equipment_ids = [eq.equipment_id for eq in dataset.equipment]
        self._record(
            rule_id="ID-002",
            dataset="equipment",
            severity=ValidationSeverity.ERROR,
            passed=len(equipment_ids) == len(set(equipment_ids)),
            checked_count=len(equipment_ids),
            failed_count=len(equipment_ids) - len(set(equipment_ids)),
            message="equipment IDs unique",
            sample_keys=tuple(
                eid for eid in equipment_ids if equipment_ids.count(eid) > 1
            )[: self._validation_config.maximum_failure_samples],
            results=results,
            issues=issues,
        )

        if not dataset.alarms.empty and "alarm_id" in dataset.alarms.columns:
            alarm_ids = dataset.alarms["alarm_id"].astype(str)
            checked = len(alarm_ids)
            failed = int(alarm_ids.duplicated().sum())
            self._record(
                rule_id="ID-003",
                dataset="alarms",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="alarm IDs unique",
                sample_keys=tuple(
                    alarm_ids[alarm_ids.duplicated()].unique()[
                        : self._validation_config.maximum_failure_samples
                    ]
                ),
                results=results,
                issues=issues,
            )

        if not dataset.incidents.empty and "incident_id" in dataset.incidents.columns:
            incident_ids = dataset.incidents["incident_id"].astype(str)
            checked = len(incident_ids)
            failed = int(incident_ids.duplicated().sum())
            self._record(
                rule_id="ID-004",
                dataset="incidents",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="incident IDs unique",
                sample_keys=tuple(
                    incident_ids[incident_ids.duplicated()].unique()[
                        : self._validation_config.maximum_failure_samples
                    ]
                ),
                results=results,
                issues=issues,
            )

        if (
            not dataset.work_orders.empty
            and "work_order_id" in dataset.work_orders.columns
        ):
            wo_ids = dataset.work_orders["work_order_id"].astype(str)
            checked = len(wo_ids)
            failed = int(wo_ids.duplicated().sum())
            self._record(
                rule_id="ID-005",
                dataset="work_orders",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="work order IDs unique",
                sample_keys=tuple(
                    wo_ids[wo_ids.duplicated()].unique()[
                        : self._validation_config.maximum_failure_samples
                    ]
                ),
                results=results,
                issues=issues,
            )

    def _validate_referential_integrity(
        self,
        dataset: SyntheticDataset,
        results: list[ValidationResult],
        issues: list[ValidationIssue],
    ) -> None:
        """Validate foreign-key relationships across datasets."""
        plant_ids = {plant.plant_id for plant in dataset.plants}
        equipment_ids = {eq.equipment_id for eq in dataset.equipment}
        meter_ids = {meter.meter_id for meter in dataset.revenue_meters}

        equipment_plant_ids = {eq.plant_id for eq in dataset.equipment}
        failed = len(equipment_plant_ids - plant_ids)
        self._record(
            rule_id="REF-001",
            dataset="equipment",
            severity=ValidationSeverity.ERROR,
            passed=failed == 0,
            checked_count=len(equipment_plant_ids),
            failed_count=failed,
            message="equipment plant_id references valid plant",
            sample_keys=tuple(sorted(equipment_plant_ids - plant_ids))[
                : self._validation_config.maximum_failure_samples
            ],
            results=results,
            issues=issues,
        )

        scada_plants = {obs.plant_id for obs in dataset.inverter_scada}
        failed = len(scada_plants - plant_ids)
        self._record(
            rule_id="REF-002",
            dataset="inverter_scada",
            severity=ValidationSeverity.ERROR,
            passed=failed == 0,
            checked_count=len(scada_plants),
            failed_count=failed,
            message="inverter scada plant_id references valid plant",
            sample_keys=tuple(sorted(scada_plants - plant_ids))[
                : self._validation_config.maximum_failure_samples
            ],
            results=results,
            issues=issues,
        )

        scada_equipment = {obs.equipment_id for obs in dataset.inverter_scada}
        failed = len(scada_equipment - equipment_ids)
        self._record(
            rule_id="REF-003",
            dataset="inverter_scada",
            severity=ValidationSeverity.ERROR,
            passed=failed == 0,
            checked_count=len(scada_equipment),
            failed_count=failed,
            message="inverter scada equipment_id references valid equipment",
            sample_keys=tuple(sorted(scada_equipment - equipment_ids))[
                : self._validation_config.maximum_failure_samples
            ],
            results=results,
            issues=issues,
        )

        plant_scada_plants = {obs.plant_id for obs in dataset.plant_scada}
        failed = len(plant_scada_plants - plant_ids)
        self._record(
            rule_id="REF-004",
            dataset="plant_scada",
            severity=ValidationSeverity.ERROR,
            passed=failed == 0,
            checked_count=len(plant_scada_plants),
            failed_count=failed,
            message="plant scada plant_id references valid plant",
            sample_keys=tuple(sorted(plant_scada_plants - plant_ids))[
                : self._validation_config.maximum_failure_samples
            ],
            results=results,
            issues=issues,
        )

        plant_scada_meters = {obs.meter_id for obs in dataset.plant_scada}
        failed = len(plant_scada_meters - meter_ids)
        self._record(
            rule_id="REF-005",
            dataset="plant_scada",
            severity=ValidationSeverity.ERROR,
            passed=failed == 0,
            checked_count=len(plant_scada_meters),
            failed_count=failed,
            message="plant scada meter_id references valid meter",
            sample_keys=tuple(sorted(plant_scada_meters - meter_ids))[
                : self._validation_config.maximum_failure_samples
            ],
            results=results,
            issues=issues,
        )

        if (
            not dataset.ground_truth_events.empty
            and "plant_id" in dataset.ground_truth_events.columns
        ):
            event_plants = set(
                dataset.ground_truth_events["plant_id"].astype(str).str.upper()
            )
            failed = len(event_plants - plant_ids)
            self._record(
                rule_id="REF-006",
                dataset="ground_truth_events",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=len(event_plants),
                failed_count=failed,
                message="ground truth plant_id references valid plant",
                sample_keys=tuple(sorted(event_plants - plant_ids))[
                    : self._validation_config.maximum_failure_samples
                ],
                results=results,
                issues=issues,
            )

        if not dataset.alarms.empty and "plant_id" in dataset.alarms.columns:
            alarm_plants = set(dataset.alarms["plant_id"].astype(str).str.upper())
            failed = len(alarm_plants - plant_ids)
            self._record(
                rule_id="REF-007",
                dataset="alarms",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=len(alarm_plants),
                failed_count=failed,
                message="alarm plant_id references valid plant",
                sample_keys=tuple(sorted(alarm_plants - plant_ids))[
                    : self._validation_config.maximum_failure_samples
                ],
                results=results,
                issues=issues,
            )

        if not dataset.incidents.empty and "plant_id" in dataset.incidents.columns:
            incident_plants = set(dataset.incidents["plant_id"].astype(str).str.upper())
            failed = len(incident_plants - plant_ids)
            self._record(
                rule_id="REF-008",
                dataset="incidents",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=len(incident_plants),
                failed_count=failed,
                message="incident plant_id references valid plant",
                sample_keys=tuple(sorted(incident_plants - plant_ids))[
                    : self._validation_config.maximum_failure_samples
                ],
                results=results,
                issues=issues,
            )

        if not dataset.work_orders.empty and "plant_id" in dataset.work_orders.columns:
            wo_plants = set(dataset.work_orders["plant_id"].astype(str).str.upper())
            failed = len(wo_plants - plant_ids)
            self._record(
                rule_id="REF-009",
                dataset="work_orders",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=len(wo_plants),
                failed_count=failed,
                message="work order plant_id references valid plant",
                sample_keys=tuple(sorted(wo_plants - plant_ids))[
                    : self._validation_config.maximum_failure_samples
                ],
                results=results,
                issues=issues,
            )

    def _validate_temporal(
        self,
        dataset: SyntheticDataset,
        results: list[ValidationResult],
        issues: list[ValidationIssue],
    ) -> None:
        """Validate time-grid coverage, UTC awareness, and interval alignment."""
        start = self._config.time.start
        end = self._config.time.end
        interval = self._config.time.interval_minutes

        if dataset.inverter_scada:
            # Check unique per (equipment_id, timestamp) not globally
            grains = [
                (obs.equipment_id, obs.timestamp) for obs in dataset.inverter_scada
            ]
            unique_grains = sorted(set(grains))
            checked = len(grains)
            failed = len(grains) - len(unique_grains)
            self._record(
                rule_id="TMP-001",
                dataset="inverter_scada",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message=(
                    "inverter scada timestamps unique per "
                    "(equipment_id, timestamp) grain"
                ),
                sample_keys=tuple(
                    ts.isoformat()
                    for eid, ts in sorted(set(grains))
                    if grains.count((eid, ts)) > 1
                )[: self._validation_config.maximum_failure_samples],
                results=results,
                issues=issues,
            )

            # Unique timestamps independently for TMP-002/TMP-003
            unique_sorted = sorted({obs.timestamp for obs in dataset.inverter_scada})

            out_of_range = [
                ts.isoformat()
                for ts in unique_sorted
                if not (start <= ts.astimezone(_UTC) < end)
            ]
            checked = len(unique_sorted)
            failed = len(out_of_range)
            self._record(
                rule_id="TMP-002",
                dataset="inverter_scada",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="inverter scada timestamps within [start, end)",
                sample_keys=tuple(
                    out_of_range[: self._validation_config.maximum_failure_samples]
                ),
                results=results,
                issues=issues,
            )

            misaligned = [
                ts.isoformat()
                for ts in unique_sorted
                if ts.minute % interval != 0 or ts.second != 0 or ts.microsecond != 0
            ]
            checked = len(unique_sorted)
            failed = len(misaligned)
            self._record(
                rule_id="TMP-003",
                dataset="inverter_scada",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="inverter scada timestamps aligned to interval",
                sample_keys=tuple(
                    misaligned[: self._validation_config.maximum_failure_samples]
                ),
                results=results,
                issues=issues,
            )

        if dataset.plant_scada:
            # Check unique per (plant_id, timestamp) not globally
            plant_grains = [
                (obs.plant_id, obs.timestamp) for obs in dataset.plant_scada
            ]
            unique_plant_grains = sorted(set(plant_grains))
            checked = len(plant_grains)
            failed = len(plant_grains) - len(unique_plant_grains)
            self._record(
                rule_id="TMP-004",
                dataset="plant_scada",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message=(
                    "plant scada timestamps unique per " "(plant_id, timestamp) grain"
                ),
                sample_keys=tuple(
                    ts.isoformat()
                    for pid, ts in sorted(set(plant_grains))
                    if plant_grains.count((pid, ts)) > 1
                )[: self._validation_config.maximum_failure_samples],
                results=results,
                issues=issues,
            )

    def _validate_volumes(
        self,
        dataset: SyntheticDataset,
        results: list[ValidationResult],
        issues: list[ValidationIssue],
    ) -> None:
        """Validate dataset volumes against configuration-derived expectations."""
        expected_plant_scada = self._config.expected_plant_scada_rows
        actual_plant_scada = len(dataset.plant_scada)
        passed = actual_plant_scada == expected_plant_scada
        self._record(
            rule_id="VOL-001",
            dataset="plant_scada",
            severity=ValidationSeverity.ERROR,
            passed=passed,
            checked_count=expected_plant_scada,
            failed_count=abs(actual_plant_scada - expected_plant_scada),
            message="plant scada row count matches configuration",
            results=results,
            issues=issues,
        )

        expected_weather = (
            self._config.portfolio.plant_count * self._config.time.interval_count
        )
        actual_weather = len(dataset.weather)
        passed = actual_weather == expected_weather
        self._record(
            rule_id="VOL-002",
            dataset="weather",
            severity=ValidationSeverity.WARNING,
            passed=passed,
            checked_count=expected_weather,
            failed_count=abs(actual_weather - expected_weather),
            message="weather row count matches expected plant*interval count",
            results=results,
            issues=issues,
        )

        meter_counts: dict[str, int] = {}
        for meter in dataset.revenue_meters:
            meter_counts[meter.plant_id] = meter_counts.get(meter.plant_id, 0) + 1
        bad_plants = [pid for pid, count in meter_counts.items() if count != 1]
        checked = len(meter_counts)
        failed = len(bad_plants)
        self._record(
            rule_id="VOL-003",
            dataset="revenue_meters",
            severity=ValidationSeverity.ERROR,
            passed=failed == 0,
            checked_count=checked,
            failed_count=failed,
            message="exactly one revenue meter per plant",
            sample_keys=tuple(
                bad_plants[: self._validation_config.maximum_failure_samples]
            ),
            results=results,
            issues=issues,
        )

    def _validate_numeric_physics(
        self,
        dataset: SyntheticDataset,
        results: list[ValidationResult],
        issues: list[ValidationIssue],
    ) -> None:
        """Validate numeric sanity and basic physics constraints."""
        if dataset.inverter_scada:
            active_power = np.array(
                [obs.active_power_kw for obs in dataset.inverter_scada], dtype=float
            )
            non_finite = ~np.isfinite(active_power)
            negative = active_power < 0
            failed = int(non_finite.sum() + negative.sum())
            checked = len(active_power)
            sample_keys = tuple(
                np.where(non_finite | negative)[0][
                    : self._validation_config.maximum_failure_samples
                ].tolist()
            )
            self._record(
                rule_id="PHY-001",
                dataset="inverter_scada",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="inverter scada active_power_kw is finite and non-negative",
                sample_keys=sample_keys,
                results=results,
                issues=issues,
            )

            interval_energy = np.array(
                [obs.interval_energy_kwh for obs in dataset.inverter_scada], dtype=float
            )
            negative_energy = interval_energy < 0
            checked = len(interval_energy)
            failed = int(negative_energy.sum())
            self._record(
                rule_id="PHY-002",
                dataset="inverter_scada",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="inverter scada interval_energy_kwh is non-negative",
                sample_keys=tuple(
                    np.where(negative_energy)[0][
                        : self._validation_config.maximum_failure_samples
                    ].tolist()
                ),
                results=results,
                issues=issues,
            )

        if dataset.plant_scada:
            export_power = np.array(
                [obs.export_power_kw for obs in dataset.plant_scada], dtype=float
            )
            negative_export = export_power < 0
            checked = len(export_power)
            failed = int(negative_export.sum())
            self._record(
                rule_id="PHY-003",
                dataset="plant_scada",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="plant scada export_power_kw is non-negative",
                sample_keys=tuple(
                    np.where(negative_export)[0][
                        : self._validation_config.maximum_failure_samples
                    ].tolist()
                ),
                results=results,
                issues=issues,
            )

            # Check monotonicity per plant (cumulative register resets per plant)
            regression_positions: list[int] = []
            checked = 0
            cumulative_by_plant: dict[str, list[float]] = {}
            for obs in dataset.plant_scada:
                cumulative_by_plant.setdefault(obs.plant_id, []).append(
                    obs.cumulative_export_energy_kwh
                )

            for _plant_id, values in sorted(cumulative_by_plant.items()):
                plant_values = np.asarray(values, dtype=float)
                plant_diffs = np.diff(plant_values)
                plant_regressions = plant_diffs < 0
                checked += max(0, len(plant_values) - 1)
                regression_positions.extend(
                    int(i) for i in np.where(plant_regressions)[0]
                )

            failed = len(regression_positions)
            self._record(
                rule_id="PHY-004",
                dataset="plant_scada",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message=(
                    "plant scada cumulative_export_energy_kwh "
                    "is non-decreasing per plant"
                ),
                sample_keys=tuple(
                    regression_positions[
                        : self._validation_config.maximum_failure_samples
                    ]
                ),
                results=results,
                issues=issues,
            )

        if dataset.weather:
            ghi = np.array([obs.ghi_wm2 for obs in dataset.weather], dtype=float)
            negative_ghi = ghi < 0
            checked = len(ghi)
            failed = int(negative_ghi.sum())
            self._record(
                rule_id="PHY-005",
                dataset="weather",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="weather ghi_wm2 is non-negative",
                sample_keys=tuple(
                    np.where(negative_ghi)[0][
                        : self._validation_config.maximum_failure_samples
                    ].tolist()
                ),
                results=results,
                issues=issues,
            )

    def _validate_lifecycle(
        self,
        dataset: SyntheticDataset,
        results: list[ValidationResult],
        issues: list[ValidationIssue],
    ) -> None:
        """Validate lifecycle ordering for alarms, incidents, and work orders."""
        if not dataset.alarms.empty:
            raised = pd.to_datetime(
                dataset.alarms["raised_at"], utc=True, errors="coerce"
            )
            cleared = pd.to_datetime(
                dataset.alarms["cleared_at"], utc=True, errors="coerce"
            )
            invalid = cleared.notna() & (cleared < raised)
            checked = int(raised.notna().sum())
            failed = int(invalid.sum())
            self._record(
                rule_id="LFC-001",
                dataset="alarms",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="alarm cleared_at is not before raised_at",
                sample_keys=tuple(
                    dataset.alarms.index[invalid].tolist()[
                        : self._validation_config.maximum_failure_samples
                    ]
                ),
                results=results,
                issues=issues,
            )

        if not dataset.incidents.empty:
            occurred = pd.to_datetime(
                dataset.incidents["occurred_at"], utc=True, errors="coerce"
            )
            resolved = pd.to_datetime(
                dataset.incidents["resolved_at"], utc=True, errors="coerce"
            )
            invalid = resolved.notna() & (resolved < occurred)
            checked = int(occurred.notna().sum())
            failed = int(invalid.sum())
            self._record(
                rule_id="LFC-002",
                dataset="incidents",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="incident resolved_at is not before occurred_at",
                sample_keys=tuple(
                    dataset.incidents.index[invalid].tolist()[
                        : self._validation_config.maximum_failure_samples
                    ]
                ),
                results=results,
                issues=issues,
            )

        if not dataset.work_orders.empty:
            created = pd.to_datetime(
                dataset.work_orders["created_at"], utc=True, errors="coerce"
            )
            completed = pd.to_datetime(
                dataset.work_orders["completed_at"], utc=True, errors="coerce"
            )
            invalid = completed.notna() & (completed < created)
            checked = int(created.notna().sum())
            failed = int(invalid.sum())
            self._record(
                rule_id="LFC-003",
                dataset="work_orders",
                severity=ValidationSeverity.ERROR,
                passed=failed == 0,
                checked_count=checked,
                failed_count=failed,
                message="work order completed_at is not before created_at",
                sample_keys=tuple(
                    dataset.work_orders.index[invalid].tolist()[
                        : self._validation_config.maximum_failure_samples
                    ]
                ),
                results=results,
                issues=issues,
            )


def validate_dataset(
    dataset: SyntheticDataset, config: GenerationConfig
) -> ValidationReport:
    """Validate a fully assembled synthetic dataset.

    This is the primary public entry point for Phase 2 validation.

    Parameters
    ----------
    dataset:
        The assembled :class:`SyntheticDataset` to validate.
    config:
        The :class:`GenerationConfig` used to generate the dataset.

    Returns
    -------
    ValidationReport
        Complete validation results and issues.
    """
    validator = SyntheticDatasetValidator(config)
    return validator.validate_dataset(dataset)


_UTC = __import__("datetime").timezone.utc

_GROUND_TRUTH_COLUMNS = (
    "ground_truth_event_id",
    "event_type",
    "event_scope",
    "plant_id",
    "asset_type",
    "asset_id",
    "parent_event_id",
    "start_at_utc",
    "end_at_utc",
    "severity",
    "severity_score",
    "power_modifier_ratio",
    "measurement_channel",
    "measurement_bias",
    "is_planned",
    "cause_code",
    "parameters_json",
    "expected_alarm_code",
    "expected_incident",
    "expected_work_order",
    "generation_run_id",
    "schema_version",
)

_ALARM_COLUMNS = (
    "alarm_id",
    "plant_id",
    "equipment_id",
    "source_asset_id",
    "source_asset_type",
    "event_scope",
    "ground_truth_event_id",
    "alarm_code",
    "alarm_name",
    "category",
    "severity",
    "raised_at",
    "status",
    "acknowledged_at",
    "cleared_at",
    "message",
    "is_open",
    "is_critical",
    "acknowledgement_seconds",
    "resolution_seconds",
    "is_synthetic_ground_truth",
    "is_nuisance",
    "incident_eligible",
    "event_type",
    "event_start_at_utc",
    "event_end_at_utc",
    "generation_run_id",
    "schema_version",
)

_INCIDENT_COLUMNS = (
    "incident_id",
    "plant_id",
    "primary_equipment_id",
    "incident_name",
    "category",
    "severity",
    "priority",
    "status",
    "owner_team",
    "occurred_at",
    "detected_at",
    "assigned_at",
    "investigation_started_at",
    "restored_at",
    "resolved_at",
    "closed_at",
    "primary_alarm_id",
    "linked_alarm_ids",
    "linked_alarm_count",
    "ground_truth_event_id",
    "description",
    "root_cause",
    "sla_response_minutes",
    "sla_resolution_minutes",
    "response_sla_breached",
    "resolution_sla_breached",
    "detection_seconds",
    "resolution_seconds",
    "is_open",
    "is_critical",
    "is_synthetic_ground_truth",
    "generation_run_id",
    "schema_version",
)

_WORK_ORDER_COLUMNS = (
    "work_order_id",
    "linked_incident_id",
    "plant_id",
    "equipment_id",
    "work_order_name",
    "work_order_type",
    "priority",
    "assigned_team",
    "status",
    "created_at",
    "scheduled_at",
    "started_at",
    "completed_at",
    "cancelled_at",
    "estimated_labor_hours",
    "actual_labor_hours",
    "estimated_cost",
    "actual_cost",
    "description",
    "completion_notes",
    "is_open",
    "is_over_budget",
    "labor_variance_hours",
    "cost_variance",
    "completion_seconds",
    "linked_alarm_ids",
    "linked_alarm_count",
    "ground_truth_event_id",
    "sla_target_hours",
    "sla_breached",
    "is_synthetic_ground_truth",
    "generation_run_id",
    "schema_version",
)

_TARIFF_COLUMNS = (
    "tariff_id",
    "plant_id",
    "tariff_type",
    "contract_name",
    "currency",
    "effective_start_date",
    "effective_end_date",
    "window_code",
    "local_start_time",
    "local_end_time",
    "day_category",
    "energy_rate_per_mwh",
    "annual_escalation_ratio",
    "generation_run_id",
    "schema_version",
)

_BUDGET_COLUMNS = (
    "budget_id",
    "plant_id",
    "budget_year",
    "budget_month",
    "budget_energy_mwh",
    "budget_revenue",
    "target_performance_ratio",
    "target_technical_availability_ratio",
    "budget_opex",
    "budget_planned_maintenance",
    "currency",
    "basis_version",
    "generation_run_id",
    "schema_version",
)


__all__ = [
    "SyntheticDatasetValidator",
    "ValidationIssue",
    "ValidationReport",
    "ValidationResult",
    "ValidationSeverity",
    "validate_dataset",
]
