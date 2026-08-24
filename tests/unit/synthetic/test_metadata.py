"""
Comprehensive unit tests for EOIP Phase 2 manifest generation and artifact integrity.

Tests cover manifest construction, checksum calculation, JSON serialization,
atomic writes, read-back validation, artifact verification, and determinism.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from eoip.core.exceptions import DataGenerationError
from eoip.synthetic.config import (
    GenerationConfig,
    GenerationProfile,
    OutputConfig,
    PortfolioConfig,
    TimeRangeConfig,
)
from eoip.synthetic.generator import GenerationSummary, SyntheticDataset
from eoip.synthetic.io import DatasetWriteResult, StagedRunDirectory
from eoip.synthetic.metadata import (
    MANIFEST_SCHEMA_VERSION,
    Manifest,
    build_manifest,
    read_manifest,
    sha256_file,
    verify_manifest_artifacts,
    write_manifest,
)
from eoip.synthetic.models.equipment import Equipment, EquipmentStatus, EquipmentType
from eoip.synthetic.models.meter import MeterAccuracyClass, MeterStatus, RevenueMeter
from eoip.synthetic.models.plant import Plant, PlantStatus
from eoip.synthetic.models.plant_scada import PlantSCADAObservation, PlantSCADAQuality
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
    SCADAQuality,
)
from eoip.synthetic.models.weather import WeatherObservation, WeatherQuality
from eoip.synthetic.random import create_random_context
from eoip.synthetic.validation import validate_dataset

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _unit_config(tmp_path: Path) -> GenerationConfig:
    """Return a small deterministic unit configuration."""
    return GenerationConfig(
        profile_name=GenerationProfile.UNIT,
        seed=20250201,
        time=TimeRangeConfig(
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 1, 3, tzinfo=UTC),
        ),
        portfolio=PortfolioConfig(
            plant_count=1,
            aggregate_ac_capacity_min_mw=20,
            aggregate_ac_capacity_max_mw=100,
            inverter_count_min=1,
            inverter_count_max=50,
        ),
        output=OutputConfig(root=tmp_path),
    )


def _plant() -> Plant:
    """Return one valid plant."""
    return Plant(
        plant_id="PLANT-001",
        plant_name="Test Plant",
        region="Test Region",
        latitude=30.0,
        longitude=-100.0,
        dc_capacity_mw=25.0,
        ac_capacity_mw=20.0,
        commissioning_date=__import__("datetime").date(2020, 1, 1),
        status=PlantStatus.OPERATIONAL,
    )


def _equipment() -> Equipment:
    """Return one valid equipment record."""
    return Equipment(
        equipment_id="EQP-00001",
        plant_id="PLANT-001",
        equipment_name="Test Inverter",
        equipment_type=EquipmentType.STRING_INVERTER,
        manufacturer="Test MFG",
        model_number="MODEL-1",
        serial_number="SN-001",
        commissioning_date=__import__("datetime").date(2020, 1, 1),
        rated_power_kw=1000.0,
        status=EquipmentStatus.OPERATIONAL,
    )


def _meter() -> RevenueMeter:
    """Return one valid revenue meter."""
    return RevenueMeter(
        meter_id="MTR-00001",
        plant_id="PLANT-001",
        equipment_id="EQP-00001",
        meter_name="Test Meter",
        manufacturer="Test MFG",
        model_number="MTR-1",
        serial_number="SN-MTR-1",
        accuracy_class=MeterAccuracyClass.CLASS_1,
        multiplier=1.0,
        calibration_date=__import__("datetime").date(2024, 1, 1),
        status=MeterStatus.ACTIVE,
        is_primary=True,
    )


def _weather(timestamp: datetime) -> WeatherObservation:
    """Return one valid weather observation."""
    return WeatherObservation(
        plant_id="PLANT-001",
        weather_station_id="WS-001",
        timestamp=timestamp,
        ghi_wm2=500.0,
        dni_wm2=400.0,
        dhi_wm2=100.0,
        ambient_temperature_c=25.0,
        module_temperature_c=45.0,
        wind_speed_ms=3.0,
        relative_humidity_pct=50.0,
        quality=WeatherQuality.VALID,
    )


def _scada(timestamp: datetime) -> SCADAObservation:
    """Return one valid SCADA observation."""
    return SCADAObservation(
        plant_id="PLANT-001",
        equipment_id="EQP-00001",
        timestamp=timestamp,
        active_power_kw=100.0,
        interval_energy_kwh=25.0,
        dc_voltage_v=1000.0,
        dc_current_a=100.0,
        ac_voltage_v=400.0,
        ac_current_a=144.0,
        frequency_hz=50.0,
        power_factor=0.99,
        equipment_available=True,
        grid_available=True,
        operating_state=SCADAOperatingState.NORMAL,
        quality=SCADAQuality.VALID,
    )


def _plant_scada(timestamp: datetime) -> PlantSCADAObservation:
    """Return one valid plant SCADA observation."""
    return PlantSCADAObservation(
        plant_id="PLANT-001",
        meter_id="MTR-00001",
        timestamp=timestamp,
        gross_inverter_power_kw=100.0,
        transformer_loss_kw=1.0,
        collection_loss_kw=0.5,
        export_power_kw=98.0,
        import_power_kw=0.0,
        interval_export_energy_kwh=24.5,
        interval_import_energy_kwh=0.0,
        cumulative_export_energy_kwh=1000.0,
        cumulative_import_energy_kwh=0.0,
        grid_available=True,
        plant_available=True,
        quality=PlantSCADAQuality.VALID,
    )


def _valid_dataset(tmp_path: Path) -> SyntheticDataset:
    """Return a minimal valid SyntheticDataset."""
    config = _unit_config(tmp_path)
    plant = _plant()
    equipment = _equipment()
    meter = _meter()
    timestamps = [
        config.time.start + __import__("datetime").timedelta(minutes=15 * i)
        for i in range(config.time.interval_count)
    ]
    weather = tuple(_weather(ts) for ts in timestamps)
    scada = tuple(_scada(ts) for ts in timestamps)
    plant_scada = tuple(_plant_scada(ts) for ts in timestamps)
    ground_truth = pd.DataFrame(
        {
            "ground_truth_event_id": ["GTE-2025-00000001"],
            "event_type": ["inverter_trip"],
            "event_scope": ["inverter"],
            "plant_id": ["PLANT-001"],
            "asset_type": ["string_inverter"],
            "asset_id": ["EQP-00001"],
            "parent_event_id": [None],
            "start_at_utc": [datetime(2025, 1, 1, 12, 0, tzinfo=UTC)],
            "end_at_utc": [datetime(2025, 1, 1, 13, 0, tzinfo=UTC)],
            "severity": ["moderate"],
            "severity_score": [0.5],
            "power_modifier_ratio": [0.0],
            "measurement_channel": [None],
            "measurement_bias": [None],
            "is_planned": [False],
            "cause_code": ["INVERTER_TRIP"],
            "parameters_json": ["{}"],
            "expected_alarm_code": [None],
            "expected_incident": [True],
            "expected_work_order": [False],
            "generation_run_id": ["RUN-20250101T000000Z-20250201"],
            "schema_version": ["1.0.0"],
        }
    )
    alarms = pd.DataFrame(
        {
            "alarm_id": ["ALM-0000001"],
            "plant_id": ["PLANT-001"],
            "equipment_id": ["EQP-00001"],
            "source_asset_id": ["EQP-00001"],
            "source_asset_type": ["string_inverter"],
            "event_scope": ["inverter"],
            "ground_truth_event_id": ["GTE-2025-00000001"],
            "alarm_code": ["INV-TRIP-001"],
            "alarm_name": ["Inverter Trip"],
            "category": ["equipment"],
            "severity": ["major"],
            "raised_at": [datetime(2025, 1, 1, 12, 0, tzinfo=UTC)],
            "status": ["active"],
            "acknowledged_at": [None],
            "cleared_at": [None],
            "message": ["Test alarm"],
            "is_open": [True],
            "is_critical": [False],
            "acknowledgement_seconds": [None],
            "resolution_seconds": [None],
            "is_synthetic_ground_truth": [True],
            "is_nuisance": [False],
            "incident_eligible": [True],
            "event_type": ["inverter_trip"],
            "event_start_at_utc": [datetime(2025, 1, 1, 12, 0, tzinfo=UTC)],
            "event_end_at_utc": [datetime(2025, 1, 1, 13, 0, tzinfo=UTC)],
            "generation_run_id": ["RUN-20250101T000000Z-20250201"],
            "schema_version": ["1.0.0"],
        }
    )
    incidents = pd.DataFrame(
        {
            "incident_id": ["INC-0000001"],
            "plant_id": ["PLANT-001"],
            "primary_equipment_id": ["EQP-00001"],
            "incident_name": ["Test Incident"],
            "category": ["equipment_failure"],
            "severity": ["moderate"],
            "priority": ["p2"],
            "status": ["open"],
            "owner_team": ["plant_operations"],
            "occurred_at": [datetime(2025, 1, 1, 12, 0, tzinfo=UTC)],
            "detected_at": [None],
            "assigned_at": [None],
            "investigation_started_at": [None],
            "restored_at": [None],
            "resolved_at": [None],
            "closed_at": [None],
            "primary_alarm_id": ["ALM-0000001"],
            "linked_alarm_ids": ["ALM-0000001"],
            "linked_alarm_count": [1],
            "ground_truth_event_id": ["GTE-2025-00000001"],
            "description": ["Test incident"],
            "root_cause": [None],
            "sla_response_minutes": [60],
            "sla_resolution_minutes": [240],
            "response_sla_breached": [False],
            "resolution_sla_breached": [False],
            "detection_seconds": [None],
            "resolution_seconds": [None],
            "is_open": [True],
            "is_critical": [False],
            "is_synthetic_ground_truth": [True],
            "generation_run_id": ["RUN-20250101T000000Z-20250201"],
            "schema_version": ["1.0.0"],
        }
    )
    work_orders = pd.DataFrame(
        {
            "work_order_id": ["WO-0000001"],
            "linked_incident_id": ["INC-0000001"],
            "plant_id": ["PLANT-001"],
            "equipment_id": ["EQP-00001"],
            "work_order_name": ["Test WO"],
            "work_order_type": ["corrective"],
            "priority": ["medium"],
            "assigned_team": ["maintenance"],
            "status": ["open"],
            "created_at": [datetime(2025, 1, 1, 12, 0, tzinfo=UTC)],
            "scheduled_at": [None],
            "started_at": [None],
            "completed_at": [None],
            "cancelled_at": [None],
            "estimated_labor_hours": [2.0],
            "actual_labor_hours": [None],
            "estimated_cost": [1000.0],
            "actual_cost": [None],
            "description": ["Test WO"],
            "completion_notes": [None],
            "is_open": [True],
            "is_over_budget": [None],
            "labor_variance_hours": [None],
            "cost_variance": [None],
            "completion_seconds": [None],
            "linked_alarm_ids": ["ALM-0000001"],
            "linked_alarm_count": [1],
            "ground_truth_event_id": ["GTE-2025-00000001"],
            "sla_target_hours": [4.0],
            "sla_breached": [False],
            "is_synthetic_ground_truth": [True],
            "generation_run_id": ["RUN-20250101T000000Z-20250201"],
            "schema_version": ["1.0.0"],
        }
    )
    tariffs = pd.DataFrame(
        {
            "tariff_id": ["TRF-0001"],
            "plant_id": ["PLANT-001"],
            "tariff_type": ["flat"],
            "contract_name": ["Test Tariff"],
            "currency": ["USD"],
            "effective_start_date": ["2025-01-01"],
            "effective_end_date": ["2025-12-31"],
            "window_code": ["ALL"],
            "local_start_time": [None],
            "local_end_time": [None],
            "day_category": ["all"],
            "energy_rate_per_mwh": [50.0],
            "annual_escalation_ratio": [0.0],
            "generation_run_id": ["RUN-20250101T000000Z-20250201"],
            "schema_version": ["1.0.0"],
        }
    )
    budgets = pd.DataFrame(
        {
            "budget_id": ["PLANT-001-2025-01"],
            "plant_id": ["PLANT-001"],
            "budget_year": [2025],
            "budget_month": [1],
            "budget_energy_mwh": [1000.0],
            "budget_revenue": [50000.0],
            "target_performance_ratio": [0.8],
            "target_technical_availability_ratio": [0.95],
            "budget_opex": [10000.0],
            "budget_planned_maintenance": [5000.0],
            "currency": ["USD"],
            "basis_version": ["1.0.0"],
            "generation_run_id": ["RUN-20250101T000000Z-20250201"],
            "schema_version": ["1.0.0"],
        }
    )
    return SyntheticDataset(
        plants=(plant,),
        equipment=(equipment,),
        revenue_meters=(meter,),
        weather=weather,
        inverter_scada=scada,
        plant_scada=plant_scada,
        ground_truth_events=ground_truth,
        alarms=alarms,
        incidents=incidents,
        work_orders=work_orders,
        tariffs=tariffs,
        budgets=budgets,
    )


def _write_dataset(
    tmp_path: Path, dataset: SyntheticDataset
) -> tuple[StagedRunDirectory, tuple[DatasetWriteResult, ...]]:
    """Write a dataset to a staging directory and return staging + results."""
    from eoip.synthetic.io import DatasetWriter

    config = _unit_config(tmp_path)
    staging = StagedRunDirectory(tmp_path, "RUN-TEST-20250201")
    writer = DatasetWriter(config, run_id="RUN-TEST-20250201")
    results = writer.write(dataset, staging)
    return staging, results


# ---------------------------------------------------------------------------
# Manifest construction tests
# ---------------------------------------------------------------------------


class TestBuildManifest:
    """Tests for build_manifest()."""

    def test_manifest_construction_from_valid_fixtures(self, tmp_path: Path) -> None:
        """Manifest builds from valid small fixtures."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert isinstance(manifest, Manifest)

    def test_manifest_identity(self, tmp_path: Path) -> None:
        """Manifest contains correct identity fields."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert manifest.manifest_schema_version == MANIFEST_SCHEMA_VERSION
        assert manifest.generation_run_id == "RUN-TEST-20250201"
        assert manifest.project_name == "Energy Operations Intelligence Platform"
        assert manifest.project_version == "0.1.0"

    def test_manifest_profile_and_seed(self, tmp_path: Path) -> None:
        """Manifest captures profile name and seed."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        assert manifest.profile_name == "unit"
        assert manifest.seed == 20250201

    def test_manifest_date_range_and_interval(self, tmp_path: Path) -> None:
        """Manifest captures generation date range and interval."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        assert manifest.generation_start == "2025-01-01T00:00:00Z"
        assert manifest.generation_end == "2025-01-03T00:00:00Z"
        assert manifest.interval_minutes == 15

    def test_manifest_configuration_fingerprint(self, tmp_path: Path) -> None:
        """Manifest includes the deterministic configuration fingerprint."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        assert manifest.config_fingerprint == config.fingerprint()
        assert len(manifest.config_fingerprint) == 64

    def test_manifest_random_context_metadata(self, tmp_path: Path) -> None:
        """Manifest includes RandomContext.manifest() output."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        assert "root_seed" in manifest.random_context_manifest
        assert "stream_version" in manifest.random_context_manifest
        assert "stream_keys" in manifest.random_context_manifest
        assert "streams" in manifest.random_context_manifest
        assert manifest.random_context_manifest["root_seed"] == 20250201

    def test_manifest_generation_summary_integration(self, tmp_path: Path) -> None:
        """Manifest includes GenerationSummary.to_record() output."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        assert manifest.generation_summary["plant_count"] == 1
        assert manifest.generation_summary["generation_run_id"] == "RUN-TEST-20250201"

    def test_manifest_validation_summary_integration(self, tmp_path: Path) -> None:
        """Manifest includes validation report summary."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        assert manifest.validation_passed == validation_report.passed
        assert manifest.validation_error_count == validation_report.error_count
        assert manifest.validation_warning_count == validation_report.warning_count
        assert manifest.validation_issue_count == validation_report.issue_count

    def test_manifest_artifact_inventory(self, tmp_path: Path) -> None:
        """Manifest includes artifact inventory from write results."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        assert len(manifest.datasets) == len(write_results)
        dataset_names = {d.dataset_name for d in manifest.datasets}
        assert "plants" in dataset_names
        assert "weather" in dataset_names
        assert "alarms" in dataset_names

    def test_manifest_artifact_checksums(self, tmp_path: Path) -> None:
        """Manifest includes SHA-256 checksums for all artifacts."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        for dataset_manifest in manifest.datasets:
            for artifact in dataset_manifest.artifacts:
                assert len(artifact.sha256) == 64
                assert all(c in "0123456789abcdef" for c in artifact.sha256)


# ---------------------------------------------------------------------------
# SHA-256 checksum tests
# ---------------------------------------------------------------------------


class TestSha256File:
    """Tests for sha256_file()."""

    def test_checksum_small_file(self, tmp_path: Path) -> None:
        """SHA-256 is correct for a small binary file."""
        test_file = tmp_path / "small.bin"
        test_file.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert sha256_file(test_file) == expected

    def test_checksum_changes_when_bytes_change(self, tmp_path: Path) -> None:
        """SHA-256 changes when file content changes."""
        file_a = tmp_path / "a.bin"
        file_b = tmp_path / "b.bin"
        file_a.write_bytes(b"content A")
        file_b.write_bytes(b"content B")
        assert sha256_file(file_a) != sha256_file(file_b)

    def test_checksum_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing file raises DataGenerationError."""
        with pytest.raises(DataGenerationError, match="Cannot checksum"):
            sha256_file(tmp_path / "nonexistent.bin")

    def test_checksum_large_file_streamed(self, tmp_path: Path) -> None:
        """Large files are checksummed without loading entirely into memory."""
        large_file = tmp_path / "large.bin"
        # Write 20 MiB of zeros
        large_file.write_bytes(b"\x00" * (20 * 1024 * 1024))
        checksum = sha256_file(large_file, chunk_size=1024 * 1024)
        assert len(checksum) == 64
        assert checksum == hashlib.sha256(b"\x00" * (20 * 1024 * 1024)).hexdigest()


# ---------------------------------------------------------------------------
# Deterministic aggregate fingerprint tests
# ---------------------------------------------------------------------------


class TestAggregateFingerprint:
    """Tests for deterministic aggregate dataset fingerprint."""

    def test_deterministic_aggregate_fingerprint(self, tmp_path: Path) -> None:
        """Same inputs produce the same aggregate fingerprint."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest_a = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        manifest_b = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
            created_at=datetime(2025, 1, 2, tzinfo=UTC),
        )
        assert (
            manifest_a.aggregate_dataset_fingerprint
            == manifest_b.aggregate_dataset_fingerprint
        )

    def test_aggregate_fingerprint_unaffected_by_created_at(
        self, tmp_path: Path
    ) -> None:
        """Aggregate fingerprint does not include created_at."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest_early = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
            created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        manifest_late = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
            created_at=datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC),
        )
        assert (
            manifest_early.aggregate_dataset_fingerprint
            == manifest_late.aggregate_dataset_fingerprint
        )

    def test_different_artifact_content_changes_fingerprint(
        self, tmp_path: Path
    ) -> None:
        """Changing artifact content changes the aggregate fingerprint."""
        config = _unit_config(tmp_path)
        dataset_a = _valid_dataset(tmp_path)
        staging_a, write_results_a = _write_dataset(tmp_path, dataset_a)
        summary_a = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset_a, config)
        manifest_a = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary_a,
            validation_report=validation_report,
            write_results=write_results_a,
        )
        # Modify one artifact file
        for result in write_results_a:
            if result.dataset_name == "plants":
                for artifact in result.artifacts:
                    artifact.path.write_bytes(b"corrupted")
                break
        manifest_b = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary_a,
            validation_report=validation_report,
            write_results=write_results_a,
        )
        assert (
            manifest_a.aggregate_dataset_fingerprint
            != manifest_b.aggregate_dataset_fingerprint
        )


# ---------------------------------------------------------------------------
# Path safety tests
# ---------------------------------------------------------------------------


class TestPathSafety:
    """Tests for manifest path safety."""

    def test_relative_portable_paths(self, tmp_path: Path) -> None:
        """Manifest uses relative paths for artifacts."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        for dataset_manifest in manifest.datasets:
            for artifact in dataset_manifest.artifacts:
                assert not artifact.relative_path.startswith("/")
                assert ".." not in artifact.relative_path

    def test_path_traversal_rejection(self, tmp_path: Path) -> None:
        """Path traversal sequences are rejected in run IDs."""
        from eoip.synthetic.io import _validate_run_id

        with pytest.raises(ValueError, match="unsafe"):
            _validate_run_id("../evil")


# ---------------------------------------------------------------------------
# JSON writing tests
# ---------------------------------------------------------------------------


class TestWriteManifest:
    """Tests for write_manifest()."""

    def test_deterministic_json_key_ordering(self, tmp_path: Path) -> None:
        """Manifest JSON keys are sorted deterministically."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        manifest_path = tmp_path / "manifest.json"
        write_manifest(manifest, manifest_path)
        raw = manifest_path.read_bytes()
        data = json.loads(raw)
        keys = list(data.keys())
        assert keys == sorted(keys)

    def test_newline_at_eof(self, tmp_path: Path) -> None:
        """Manifest JSON ends with a newline."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        manifest_path = tmp_path / "manifest.json"
        write_manifest(manifest, manifest_path)
        raw = manifest_path.read_bytes()
        assert raw.endswith(b"\n")

    def test_atomic_manifest_replacement(self, tmp_path: Path) -> None:
        """Manifest write uses atomic replacement."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        manifest_path = tmp_path / "manifest.json"
        write_manifest(manifest, manifest_path)
        assert manifest_path.is_file()
        assert not manifest_path.with_suffix(manifest_path.suffix + ".tmp").exists()

    def test_read_manifest_round_trip(self, tmp_path: Path) -> None:
        """Manifest can be written and read back identically."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        manifest_path = tmp_path / "manifest.json"
        write_manifest(manifest, manifest_path)
        loaded = read_manifest(manifest_path)
        assert loaded.generation_run_id == manifest.generation_run_id
        assert loaded.config_fingerprint == manifest.config_fingerprint
        assert (
            loaded.aggregate_dataset_fingerprint
            == manifest.aggregate_dataset_fingerprint
        )
        assert loaded.created_at == manifest.created_at

    def test_malformed_json_handling(self, tmp_path: Path) -> None:
        """Malformed JSON raises DataGenerationError."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_bytes(b"{not valid json")
        with pytest.raises(DataGenerationError, match="Malformed JSON"):
            read_manifest(bad_file)

    def test_unsupported_manifest_version_handling(self, tmp_path: Path) -> None:
        """Unsupported manifest schema version raises DataGenerationError."""
        bad_file = tmp_path / "bad_version.json"
        bad_file.write_bytes(b'{"manifest_schema_version": "2.0.0"}')
        with pytest.raises(
            DataGenerationError, match="Unsupported manifest schema version"
        ):
            read_manifest(bad_file)

    def test_missing_manifest_file_raises(self, tmp_path: Path) -> None:
        """Missing manifest file raises DataGenerationError."""
        with pytest.raises(DataGenerationError, match="Manifest file not found"):
            read_manifest(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# Artifact verification tests
# ---------------------------------------------------------------------------


class TestVerifyManifestArtifacts:
    """Tests for verify_manifest_artifacts()."""

    def test_missing_artifact_detection(self, tmp_path: Path) -> None:
        """Missing artifact files are detected."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        # Delete one artifact
        for dataset_manifest in manifest.datasets:
            if dataset_manifest.artifacts:
                artifact_path = (
                    staging.staging_path / dataset_manifest.artifacts[0].relative_path
                )
                if artifact_path.exists():
                    artifact_path.unlink()
                    break
        ok, errors = verify_manifest_artifacts(manifest, staging.staging_path)
        assert ok is False
        assert any("Missing artifact" in e for e in errors)

    def test_corrupted_artifact_checksum_detection(self, tmp_path: Path) -> None:
        """Corrupted artifact files are detected by checksum mismatch."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        # Corrupt one artifact
        for dataset_manifest in manifest.datasets:
            if dataset_manifest.artifacts:
                artifact_path = (
                    staging.staging_path / dataset_manifest.artifacts[0].relative_path
                )
                if artifact_path.exists():
                    artifact_path.write_bytes(b"corrupted")
                    break
        ok, errors = verify_manifest_artifacts(manifest, staging.staging_path)
        assert ok is False
        assert any("Checksum mismatch" in e for e in errors)

    def test_verify_valid_artifacts_passes(self, tmp_path: Path) -> None:
        """Verification passes when all artifacts are present and correct."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        manifest = build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        ok, errors = verify_manifest_artifacts(manifest, staging.staging_path)
        assert ok is True
        assert errors == []


# ---------------------------------------------------------------------------
# Source immutability tests
# ---------------------------------------------------------------------------


class TestSourceImmutability:
    """Tests that manifest operations do not mutate source objects."""

    def test_source_objects_not_mutated(self, tmp_path: Path) -> None:
        """Building a manifest does not mutate source objects."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        original_summary_dict = summary.to_record()
        original_random_manifest = random_context.manifest()
        build_manifest(
            config=config,
            random_context=random_context,
            summary=summary,
            validation_report=validation_report,
            write_results=write_results,
        )
        assert summary.to_record() == original_summary_dict
        assert random_context.manifest() == original_random_manifest


# ---------------------------------------------------------------------------
# Invalid input tests
# ---------------------------------------------------------------------------


class TestInvalidInputs:
    """Tests for invalid input handling."""

    def test_invalid_config_type_raises(self, tmp_path: Path) -> None:
        """build_manifest rejects invalid config type."""
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(20250201)
        validation_report = validate_dataset(dataset, _unit_config(tmp_path))
        with pytest.raises(TypeError):
            build_manifest(
                config="not-a-config",  # type: ignore[arg-type]
                random_context=random_context,
                summary=summary,
                validation_report=validation_report,
                write_results=write_results,
            )

    def test_invalid_summary_type_raises(self, tmp_path: Path) -> None:
        """build_manifest rejects invalid summary type."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        with pytest.raises(TypeError):
            build_manifest(
                config=config,
                random_context=random_context,
                summary="not-a-summary",  # type: ignore[arg-type]
                validation_report=validation_report,
                write_results=write_results,
            )

    def test_invalid_validation_report_type_raises(self, tmp_path: Path) -> None:
        """build_manifest rejects invalid validation report type."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        staging, write_results = _write_dataset(tmp_path, dataset)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        with pytest.raises(TypeError):
            build_manifest(
                config=config,
                random_context=random_context,
                summary=summary,
                validation_report="not-a-report",  # type: ignore[arg-type]
                write_results=write_results,
            )

    def test_invalid_write_results_type_raises(self, tmp_path: Path) -> None:
        """build_manifest rejects invalid write results type."""
        config = _unit_config(tmp_path)
        dataset = _valid_dataset(tmp_path)
        summary = GenerationSummary(
            plant_count=1,
            equipment_count=1,
            revenue_meter_count=1,
            weather_count=192,
            inverter_scada_count=192,
            plant_scada_count=192,
            ground_truth_event_count=1,
            alarm_count=1,
            incident_count=1,
            work_order_count=1,
            tariff_count=1,
            budget_count=1,
            generation_run_id="RUN-TEST-20250201",
        )
        random_context = create_random_context(config.seed)
        validation_report = validate_dataset(dataset, config)
        with pytest.raises(TypeError):
            build_manifest(
                config=config,
                random_context=random_context,
                summary=summary,
                validation_report=validation_report,
                write_results="not-a-tuple",  # type: ignore[arg-type]
            )
