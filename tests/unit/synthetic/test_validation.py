"""Comprehensive unit tests for the Phase 2 synthetic validation engine."""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from eoip.synthetic.config import (
    GenerationConfig,
    GenerationProfile,
    PortfolioConfig,
    TimeRangeConfig,
    ValidationConfig,
)
from eoip.synthetic.generator import SyntheticDataset
from eoip.synthetic.models.alarm import Alarm, AlarmCategory, AlarmSeverity, AlarmStatus
from eoip.synthetic.models.equipment import Equipment, EquipmentStatus, EquipmentType
from eoip.synthetic.models.incident import (
    Incident,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)
from eoip.synthetic.models.meter import MeterAccuracyClass, MeterStatus, RevenueMeter
from eoip.synthetic.models.plant import Plant, PlantStatus
from eoip.synthetic.models.plant_scada import PlantSCADAObservation, PlantSCADAQuality
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
    SCADAQuality,
)
from eoip.synthetic.models.weather import WeatherObservation, WeatherQuality
from eoip.synthetic.models.work_order import (
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
)
from eoip.synthetic.validation import (
    ValidationIssue,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    validate_dataset,
)


def _unit_config() -> GenerationConfig:
    """Return a minimal unit-profile generation configuration."""
    return GenerationConfig(
        profile_name=GenerationProfile.UNIT,
        seed=20_250_201,
        time=TimeRangeConfig(
            start=datetime(2025, 1, 1, tzinfo=UTC),
            end=datetime(2025, 1, 3, tzinfo=UTC),
        ),
        portfolio=PortfolioConfig(
            plant_count=1,
            aggregate_ac_capacity_min_mw=20,
            aggregate_ac_capacity_max_mw=100,
            inverter_count_min=1,
            inverter_count_max=50,
        ),
        output=__import__(
            "eoip.synthetic.config", fromlist=["OutputConfig"]
        ).OutputConfig(root=__import__("pathlib").Path("data/synthetic/unit")),
    )


def _valid_plant() -> Plant:
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


def _valid_equipment(plant_id: str = "PLANT-001") -> Equipment:
    """Return one valid equipment record."""
    return Equipment(
        equipment_id="EQP-00001",
        plant_id=plant_id,
        equipment_name="Test Inverter",
        equipment_type=EquipmentType.STRING_INVERTER,
        manufacturer="Test MFG",
        model_number="MODEL-1",
        serial_number="SN-001",
        commissioning_date=__import__("datetime").date(2020, 1, 1),
        rated_power_kw=1000.0,
        status=EquipmentStatus.OPERATIONAL,
    )


def _valid_meter(plant_id: str = "PLANT-001") -> RevenueMeter:
    """Return one valid revenue meter."""
    return RevenueMeter(
        meter_id="MTR-00001",
        plant_id=plant_id,
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


def _valid_weather(
    plant_id: str = "PLANT-001",
    station_id: str = "WS-001",
    timestamp: datetime | None = None,
) -> WeatherObservation:
    """Return one valid weather observation."""
    if timestamp is None:
        timestamp = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    return WeatherObservation(
        plant_id=plant_id,
        weather_station_id=station_id,
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


def _valid_scada(
    plant_id: str = "PLANT-001",
    eq_id: str = "EQP-00001",
    timestamp: datetime | None = None,
) -> SCADAObservation:
    """Return one valid SCADA observation."""
    if timestamp is None:
        timestamp = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    return SCADAObservation(
        plant_id=plant_id,
        equipment_id=eq_id,
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


def _valid_plant_scada(
    plant_id: str = "PLANT-001",
    meter_id: str = "MTR-00001",
    timestamp: datetime | None = None,
) -> PlantSCADAObservation:
    """Return one valid plant SCADA observation."""
    if timestamp is None:
        timestamp = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    return PlantSCADAObservation(
        plant_id=plant_id,
        meter_id=meter_id,
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


def _valid_alarm(plant_id: str = "PLANT-001", eq_id: str = "EQP-00001") -> Alarm:
    """Return one valid alarm."""
    return Alarm(
        alarm_id="ALM-0000001",
        plant_id=plant_id,
        equipment_id=eq_id,
        alarm_code="TEST-001",
        alarm_name="Test Alarm",
        category=AlarmCategory.EQUIPMENT,
        severity=AlarmSeverity.WARNING,
        raised_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        status=AlarmStatus.ACTIVE,
        acknowledged_at=None,
        cleared_at=None,
        message="Test alarm message",
        is_synthetic_ground_truth=False,
    )


def _valid_incident(plant_id: str = "PLANT-001", eq_id: str = "EQP-00001") -> Incident:
    """Return one valid incident."""
    return Incident(
        incident_id="INC-0000001",
        plant_id=plant_id,
        equipment_id=eq_id,
        incident_name="Test Incident",
        category=IncidentCategory.EQUIPMENT_FAILURE,
        severity=IncidentSeverity.MODERATE,
        occurred_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        status=IncidentStatus.OPEN,
        detected_at=None,
        resolved_at=None,
        description="Test incident",
        root_cause=None,
        linked_alarm_id=None,
        is_synthetic_ground_truth=False,
    )


def _valid_work_order(
    plant_id: str = "PLANT-001", eq_id: str = "EQP-00001"
) -> WorkOrder:
    """Return one valid work order."""
    return WorkOrder(
        work_order_id="WO-0000001",
        plant_id=plant_id,
        equipment_id=eq_id,
        work_order_name="Test Work Order",
        work_order_type=WorkOrderType.CORRECTIVE,
        priority=WorkOrderPriority.MEDIUM,
        created_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        status=WorkOrderStatus.OPEN,
        linked_incident_id=None,
        assigned_team=None,
        scheduled_at=None,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        estimated_labor_hours=2.0,
        actual_labor_hours=None,
        estimated_cost=1000.0,
        actual_cost=None,
        description="Test WO",
        completion_notes=None,
        is_synthetic_ground_truth=False,
    )


def _valid_dataset(config: GenerationConfig | None = None) -> SyntheticDataset:
    """Return a minimal valid SyntheticDataset."""
    if config is None:
        config = _unit_config()
    plant = _valid_plant()
    equipment = _valid_equipment()
    meter = _valid_meter()
    interval_count = config.time.interval_count
    timestamps = [
        config.time.start + timedelta(minutes=15 * i) for i in range(interval_count)
    ]
    weather = tuple(_valid_weather(timestamp=ts) for ts in timestamps)
    scada = tuple(_valid_scada(timestamp=ts) for ts in timestamps)
    plant_scada = tuple(_valid_plant_scada(timestamp=ts) for ts in timestamps)
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


class TestValidationSeverity:
    """Tests for ValidationSeverity enum."""

    def test_error_value(self) -> None:
        assert ValidationSeverity.ERROR.value == "error"

    def test_warning_value(self) -> None:
        assert ValidationSeverity.WARNING.value == "warning"


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_to_dict_serialization(self) -> None:
        issue = ValidationIssue(
            rule_id="TEST-001",
            severity=ValidationSeverity.ERROR,
            dataset="plants",
            message="test message",
            identifier="PLANT-001",
            sample_records=(1, 2, 3),
        )
        result = issue.to_dict()
        assert result["rule_id"] == "TEST-001"
        assert result["severity"] == "error"
        assert result["dataset"] == "plants"
        assert result["message"] == "test message"
        assert result["identifier"] == "PLANT-001"
        assert result["sample_records"] == [1, 2, 3]


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_to_dict_serialization(self) -> None:
        result = ValidationResult(
            rule_id="TEST-001",
            dataset="plants",
            severity=ValidationSeverity.ERROR,
            passed=False,
            checked_count=10,
            failed_count=2,
            message="test",
            sample_keys=(1, 2),
        )
        result_dict = result.to_dict()
        assert result_dict["rule_id"] == "TEST-001"
        assert result_dict["passed"] is False
        assert result_dict["checked_count"] == 10
        assert result_dict["failed_count"] == 2
        assert result_dict["sample_keys"] == [1, 2]


class TestValidationReport:
    """Tests for ValidationReport dataclass."""

    def test_passed_no_issues(self) -> None:
        config = ValidationConfig()
        report = ValidationReport(config=config)
        assert report.passed is True

    def test_passed_with_error_issue(self) -> None:
        config = ValidationConfig()
        issue = ValidationIssue(
            rule_id="TEST-001",
            severity=ValidationSeverity.ERROR,
            dataset="plants",
            message="error",
        )
        report = ValidationReport(config=config, issues=(issue,))
        assert report.passed is False

    def test_passed_with_warning_issue_fail_on_warning_false(self) -> None:
        config = ValidationConfig(fail_on_warning=False)
        issue = ValidationIssue(
            rule_id="TEST-001",
            severity=ValidationSeverity.WARNING,
            dataset="plants",
            message="warning",
        )
        report = ValidationReport(config=config, issues=(issue,))
        assert report.passed is True

    def test_passed_with_warning_issue_fail_on_warning_true(self) -> None:
        config = ValidationConfig(fail_on_warning=True)
        issue = ValidationIssue(
            rule_id="TEST-001",
            severity=ValidationSeverity.WARNING,
            dataset="plants",
            message="warning",
        )
        report = ValidationReport(config=config, issues=(issue,))
        assert report.passed is False

    def test_error_count(self) -> None:
        config = ValidationConfig()
        issues = (
            ValidationIssue(
                rule_id="E1",
                severity=ValidationSeverity.ERROR,
                dataset="a",
                message="e1",
            ),
            ValidationIssue(
                rule_id="E2",
                severity=ValidationSeverity.ERROR,
                dataset="b",
                message="e2",
            ),
            ValidationIssue(
                rule_id="W1",
                severity=ValidationSeverity.WARNING,
                dataset="c",
                message="w1",
            ),
        )
        report = ValidationReport(config=config, issues=issues)
        assert report.error_count == 2
        assert report.warning_count == 1
        assert report.issue_count == 3

    def test_to_dict_serialization(self) -> None:
        config = ValidationConfig()
        issue = ValidationIssue(
            rule_id="TEST-001",
            severity=ValidationSeverity.ERROR,
            dataset="plants",
            message="test",
        )
        report = ValidationReport(config=config, issues=(issue,))
        result = report.to_dict()
        assert result["passed"] is False
        assert result["error_count"] == 1
        assert result["warning_count"] == 0
        assert result["issue_count"] == 1
        assert len(result["issues"]) == 1


class TestSyntheticDatasetValidator:
    """Tests for the main validator class."""

    def test_valid_dataset_passes(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        report = validate_dataset(dataset, config)
        assert report.passed is True
        assert report.error_count == 0
        assert report.warning_count == 0

    def test_deterministic_result(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        report1 = validate_dataset(dataset, config)
        report2 = validate_dataset(dataset, config)
        assert report1.to_dict() == report2.to_dict()

    def test_invalid_input_type_raises(self) -> None:
        config = _unit_config()
        with pytest.raises(TypeError):
            validate_dataset("not a dataset", config)  # type: ignore[arg-type]

    def test_invalid_config_type_raises(self) -> None:
        dataset = _valid_dataset()
        with pytest.raises(TypeError):
            validate_dataset(dataset, "not a config")  # type: ignore[arg-type]

    def test_missing_required_dataframe_column_detected(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        modified_alarms = dataset.alarms.drop(columns=["alarm_id"])
        dataset = replace(dataset, alarms=modified_alarms)
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "SCH-001" for issue in report.issues)

    def test_duplicate_plant_id_detected(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        duplicate_plant = _valid_plant()
        dataset = replace(dataset, plants=(_valid_plant(), duplicate_plant))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "ID-001" for issue in report.issues)

    def test_duplicate_equipment_id_detected(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        dataset = replace(dataset, equipment=(_valid_equipment(), _valid_equipment()))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "ID-002" for issue in report.issues)

    def test_dangling_equipment_plant_reference(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        bad_equipment = Equipment(
            equipment_id="EQP-00002",
            plant_id="PLANT-999",
            equipment_name="Bad Equipment",
            equipment_type=EquipmentType.STRING_INVERTER,
            manufacturer="MFG",
            model_number="MODEL",
            serial_number="SN",
            commissioning_date=__import__("datetime").date(2020, 1, 1),
            rated_power_kw=100.0,
            status=EquipmentStatus.OPERATIONAL,
        )
        dataset = replace(dataset, equipment=(_valid_equipment(), bad_equipment))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "REF-001" for issue in report.issues)

    def test_dangling_scada_equipment_reference(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        bad_scada = SCADAObservation(
            plant_id="PLANT-001",
            equipment_id="EQP-99999",
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
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
        dataset = replace(dataset, inverter_scada=(_valid_scada(), bad_scada))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "REF-003" for issue in report.issues)

    def test_dangling_plant_scada_meter_reference(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        bad_plant_scada = PlantSCADAObservation(
            plant_id="PLANT-001",
            meter_id="MTR-99999",
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
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
        dataset = replace(dataset, plant_scada=(_valid_plant_scada(), bad_plant_scada))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "REF-005" for issue in report.issues)

    def test_timestamp_outside_configured_range(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        out_of_range = SCADAObservation(
            plant_id="PLANT-001",
            equipment_id="EQP-00001",
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
        dataset = replace(dataset, inverter_scada=(_valid_scada(), out_of_range))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "TMP-002" for issue in report.issues)

    def test_duplicate_time_series_grain(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        duplicate_scada = _valid_scada()
        dataset = replace(dataset, inverter_scada=(_valid_scada(), duplicate_scada))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "TMP-001" for issue in report.issues)

    def test_interval_misalignment(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        scada_list = list(dataset.inverter_scada)
        bad_scada = object.__new__(type(scada_list[0]))
        object.__setattr__(bad_scada, "plant_id", "PLANT-001")
        object.__setattr__(bad_scada, "equipment_id", "EQP-00001")
        object.__setattr__(
            bad_scada, "timestamp", datetime(2025, 1, 1, 12, 7, tzinfo=UTC)
        )
        object.__setattr__(bad_scada, "active_power_kw", 100.0)
        object.__setattr__(bad_scada, "interval_energy_kwh", 25.0)
        object.__setattr__(bad_scada, "dc_voltage_v", 1000.0)
        object.__setattr__(bad_scada, "dc_current_a", 100.0)
        object.__setattr__(bad_scada, "ac_voltage_v", 400.0)
        object.__setattr__(bad_scada, "ac_current_a", 144.0)
        object.__setattr__(bad_scada, "frequency_hz", 50.0)
        object.__setattr__(bad_scada, "power_factor", 0.99)
        object.__setattr__(bad_scada, "equipment_available", True)
        object.__setattr__(bad_scada, "grid_available", True)
        object.__setattr__(bad_scada, "operating_state", SCADAOperatingState.NORMAL)
        object.__setattr__(bad_scada, "quality", SCADAQuality.VALID)
        scada_list[0] = bad_scada
        dataset = replace(dataset, inverter_scada=tuple(scada_list))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "TMP-003" for issue in report.issues)

    def test_non_finite_numeric_value(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        scada_list = list(dataset.inverter_scada)
        nan_scada = object.__new__(type(scada_list[0]))
        object.__setattr__(nan_scada, "plant_id", "PLANT-001")
        object.__setattr__(nan_scada, "equipment_id", "EQP-00001")
        object.__setattr__(
            nan_scada, "timestamp", datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
        )
        object.__setattr__(nan_scada, "active_power_kw", float("nan"))
        object.__setattr__(nan_scada, "interval_energy_kwh", 25.0)
        object.__setattr__(nan_scada, "dc_voltage_v", 1000.0)
        object.__setattr__(nan_scada, "dc_current_a", 100.0)
        object.__setattr__(nan_scada, "ac_voltage_v", 400.0)
        object.__setattr__(nan_scada, "ac_current_a", 144.0)
        object.__setattr__(nan_scada, "frequency_hz", 50.0)
        object.__setattr__(nan_scada, "power_factor", 0.99)
        object.__setattr__(nan_scada, "equipment_available", True)
        object.__setattr__(nan_scada, "grid_available", True)
        object.__setattr__(nan_scada, "operating_state", SCADAOperatingState.NORMAL)
        object.__setattr__(nan_scada, "quality", SCADAQuality.VALID)
        scada_list[0] = nan_scada
        dataset = replace(dataset, inverter_scada=tuple(scada_list))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "PHY-001" for issue in report.issues)

    def test_negative_energy_where_prohibited(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        scada_list = list(dataset.inverter_scada)
        negative_scada = object.__new__(type(scada_list[0]))
        object.__setattr__(negative_scada, "plant_id", "PLANT-001")
        object.__setattr__(negative_scada, "equipment_id", "EQP-00001")
        object.__setattr__(
            negative_scada, "timestamp", datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
        )
        object.__setattr__(negative_scada, "active_power_kw", 100.0)
        object.__setattr__(negative_scada, "interval_energy_kwh", -10.0)
        object.__setattr__(negative_scada, "dc_voltage_v", 1000.0)
        object.__setattr__(negative_scada, "dc_current_a", 100.0)
        object.__setattr__(negative_scada, "ac_voltage_v", 400.0)
        object.__setattr__(negative_scada, "ac_current_a", 144.0)
        object.__setattr__(negative_scada, "frequency_hz", 50.0)
        object.__setattr__(negative_scada, "power_factor", 0.99)
        object.__setattr__(negative_scada, "equipment_available", True)
        object.__setattr__(negative_scada, "grid_available", True)
        object.__setattr__(
            negative_scada, "operating_state", SCADAOperatingState.NORMAL
        )
        object.__setattr__(negative_scada, "quality", SCADAQuality.VALID)
        scada_list[0] = negative_scada
        dataset = replace(dataset, inverter_scada=tuple(scada_list))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "PHY-002" for issue in report.issues)

    def test_cumulative_meter_register_regression(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        plant_scada_list = list(dataset.plant_scada)
        regression_scada = object.__new__(type(plant_scada_list[0]))
        object.__setattr__(regression_scada, "plant_id", "PLANT-001")
        object.__setattr__(regression_scada, "meter_id", "MTR-00001")
        object.__setattr__(
            regression_scada, "timestamp", datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
        )
        object.__setattr__(regression_scada, "gross_inverter_power_kw", 100.0)
        object.__setattr__(regression_scada, "transformer_loss_kw", 1.0)
        object.__setattr__(regression_scada, "collection_loss_kw", 0.5)
        object.__setattr__(regression_scada, "export_power_kw", 98.0)
        object.__setattr__(regression_scada, "import_power_kw", 0.0)
        object.__setattr__(regression_scada, "interval_export_energy_kwh", 24.5)
        object.__setattr__(regression_scada, "interval_import_energy_kwh", 0.0)
        object.__setattr__(regression_scada, "cumulative_export_energy_kwh", 1000.0)
        object.__setattr__(regression_scada, "cumulative_import_energy_kwh", 0.0)
        object.__setattr__(regression_scada, "grid_available", True)
        object.__setattr__(regression_scada, "plant_available", True)
        object.__setattr__(regression_scada, "quality", PlantSCADAQuality.VALID)
        plant_scada_list[0] = regression_scada
        if len(plant_scada_list) > 1:
            second = object.__new__(type(plant_scada_list[1]))
            object.__setattr__(second, "plant_id", "PLANT-001")
            object.__setattr__(second, "meter_id", "MTR-00001")
            object.__setattr__(
                second, "timestamp", datetime(2025, 1, 1, 12, 15, tzinfo=UTC)
            )
            object.__setattr__(second, "gross_inverter_power_kw", 100.0)
            object.__setattr__(second, "transformer_loss_kw", 1.0)
            object.__setattr__(second, "collection_loss_kw", 0.5)
            object.__setattr__(second, "export_power_kw", 98.0)
            object.__setattr__(second, "import_power_kw", 0.0)
            object.__setattr__(second, "interval_export_energy_kwh", 24.5)
            object.__setattr__(second, "interval_import_energy_kwh", 0.0)
            object.__setattr__(second, "cumulative_export_energy_kwh", 900.0)
            object.__setattr__(second, "cumulative_import_energy_kwh", 0.0)
            object.__setattr__(second, "grid_available", True)
            object.__setattr__(second, "plant_available", True)
            object.__setattr__(second, "quality", PlantSCADAQuality.VALID)
            plant_scada_list[1] = second
        dataset = replace(dataset, plant_scada=tuple(plant_scada_list))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "PHY-004" for issue in report.issues)

    def test_invalid_lifecycle_ordering_alarm(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        bad_alarms = pd.DataFrame(
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
                "status": ["cleared"],
                "acknowledged_at": [None],
                "cleared_at": [datetime(2025, 1, 1, 11, 0, tzinfo=UTC)],
                "message": ["Test alarm"],
                "is_open": [False],
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
        dataset = replace(dataset, alarms=bad_alarms)
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(issue.rule_id == "LFC-001" for issue in report.issues)

    def test_maximum_failure_samples_behavior(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        dataset = replace(dataset, plants=(_valid_plant(), _valid_plant()))
        report = validate_dataset(dataset, config)
        duplicate_issue = next(
            issue for issue in report.issues if issue.rule_id == "ID-001"
        )
        assert (
            len(duplicate_issue.sample_records)
            <= config.validation.maximum_failure_samples
        )

    def test_fail_on_warning_behavior(self) -> None:
        config = replace(
            _unit_config(), validation=ValidationConfig(fail_on_warning=True)
        )
        dataset = _valid_dataset(config)
        dataset = replace(dataset, weather=(_valid_weather(), _valid_weather()))
        report = validate_dataset(dataset, config)
        assert report.passed is False
        assert any(
            issue.severity == ValidationSeverity.WARNING for issue in report.issues
        )

    def test_validator_does_not_mutate_dataset(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        original_plants = copy.deepcopy(dataset.plants)
        original_alarms = dataset.alarms.copy()
        validate_dataset(dataset, config)
        assert dataset.plants == original_plants
        pd.testing.assert_frame_equal(dataset.alarms, original_alarms)

    def test_result_and_report_serialization(self) -> None:
        config = _unit_config()
        dataset = _valid_dataset(config)
        report = validate_dataset(dataset, config)
        report_dict = report.to_dict()
        assert isinstance(report_dict, dict)
        assert "passed" in report_dict
        assert "results" in report_dict
        assert "issues" in report_dict
        for result in report_dict["results"]:
            assert isinstance(result, dict)
            assert "rule_id" in result
            assert "passed" in result
        for issue in report_dict["issues"]:
            assert isinstance(issue, dict)
            assert "rule_id" in issue
            assert "severity" in issue
