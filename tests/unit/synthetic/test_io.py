"""Unit tests for the EOIP Phase 2 output pipeline and Parquet export layer."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from eoip.core.exceptions import DataGenerationError
from eoip.synthetic import io
from eoip.synthetic.config import (
    CompressionCodec,
    GenerationConfig,
    GenerationProfile,
    OutputConfig,
    OverwritePolicy,
    PortfolioConfig,
    TimeRangeConfig,
)
from eoip.synthetic.generator import SyntheticDataset
from eoip.synthetic.models.equipment import Equipment, EquipmentStatus, EquipmentType
from eoip.synthetic.models.meter import MeterAccuracyClass, MeterStatus, RevenueMeter
from eoip.synthetic.models.plant import Plant, PlantStatus
from eoip.synthetic.models.plant_scada import (
    PlantSCADAObservation,
    PlantSCADAQuality,
)
from eoip.synthetic.models.scada import (
    SCADAObservation,
    SCADAOperatingState,
    SCADAQuality,
)
from eoip.synthetic.models.weather import WeatherObservation, WeatherQuality

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------


def _config(tmp_path: Path) -> GenerationConfig:
    """Return a small deterministic unit configuration rooted at tmp_path."""
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
    return Plant(
        plant_id="PLANT-001",
        plant_name="Test Plant",
        region="Test Region",
        latitude=30.0,
        longitude=-100.0,
        dc_capacity_mw=100.0,
        ac_capacity_mw=80.0,
        commissioning_date=date(2020, 1, 1),
        status=PlantStatus.OPERATIONAL,
    )


def _equipment() -> Equipment:
    return Equipment(
        equipment_id="EQP-00001",
        plant_id="PLANT-001",
        equipment_name="Inverter 1",
        equipment_type=EquipmentType.STRING_INVERTER,
        manufacturer="TestMfg",
        model_number="MODEL-1",
        serial_number="SN-001",
        commissioning_date=date(2020, 1, 1),
        rated_power_kw=1_000.0,
        status=EquipmentStatus.OPERATIONAL,
    )


def _meter() -> RevenueMeter:
    return RevenueMeter(
        meter_id="MTR-00001",
        plant_id="PLANT-001",
        equipment_id="EQP-00001",
        meter_name="Main Meter",
        manufacturer="TestMfg",
        model_number="M-1",
        serial_number="MSN-001",
        accuracy_class=MeterAccuracyClass.CLASS_05S,
        multiplier=1.0,
        calibration_date=date(2024, 1, 1),
        status=MeterStatus.ACTIVE,
        is_primary=True,
    )


def _weather(timestamp: datetime) -> WeatherObservation:
    return WeatherObservation(
        plant_id="PLANT-001",
        weather_station_id="WS-001",
        timestamp=timestamp,
        ghi_wm2=500.0,
        dni_wm2=600.0,
        dhi_wm2=100.0,
        ambient_temperature_c=25.0,
        module_temperature_c=40.0,
        wind_speed_ms=3.0,
        relative_humidity_pct=50.0,
        quality=WeatherQuality.VALID,
    )


def _scada(timestamp: datetime) -> SCADAObservation:
    return SCADAObservation(
        plant_id="PLANT-001",
        equipment_id="EQP-00001",
        timestamp=timestamp,
        active_power_kw=100.0,
        interval_energy_kwh=25.0,
        dc_voltage_v=500.0,
        dc_current_a=200.0,
        ac_voltage_v=400.0,
        ac_current_a=150.0,
        frequency_hz=50.0,
        power_factor=0.99,
        equipment_available=True,
        grid_available=True,
        operating_state=SCADAOperatingState.NORMAL,
        quality=SCADAQuality.VALID,
    )


def _plant_scada(timestamp: datetime) -> PlantSCADAObservation:
    return PlantSCADAObservation(
        plant_id="PLANT-001",
        meter_id="MTR-00001",
        timestamp=timestamp,
        gross_inverter_power_kw=100.0,
        transformer_loss_kw=1.5,
        collection_loss_kw=1.0,
        export_power_kw=97.5,
        import_power_kw=0.0,
        interval_export_energy_kwh=24.375,
        interval_import_energy_kwh=0.0,
        cumulative_export_energy_kwh=24.375,
        cumulative_import_energy_kwh=0.0,
        grid_available=True,
        plant_available=True,
        quality=PlantSCADAQuality.VALID,
    )


def _ground_truth_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ground_truth_event_id": "GTE-2025-00000001",
                "event_type": "grid_outage",
                "event_scope": "plant",
                "plant_id": "PLANT-001",
                "asset_type": "plant",
                "asset_id": "PLANT-001",
                "parent_event_id": None,
                "start_at_utc": datetime(2025, 1, 1, 6, 0, tzinfo=UTC),
                "end_at_utc": datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
                "severity": "critical",
                "severity_score": 0.9,
                "power_modifier_ratio": None,
                "measurement_channel": None,
                "measurement_bias": None,
                "is_planned": False,
                "cause_code": "GRID_OUTAGE",
                "parameters_json": "{}",
                "expected_alarm_code": None,
                "expected_incident": True,
                "expected_work_order": False,
                "generation_run_id": "RUN-TEST",
                "schema_version": "1.0.0",
            }
        ]
    )


def _alarms_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "alarm_id": "ALM-0000001",
                "plant_id": "PLANT-001",
                "equipment_id": "EQP-00001",
                "source_asset_id": "PLANT-001",
                "source_asset_type": "plant",
                "event_scope": "plant",
                "ground_truth_event_id": "GTE-2025-00000001",
                "alarm_code": "GRID-LOSS-001",
                "alarm_name": "Grid Loss",
                "category": "grid",
                "severity": "critical",
                "raised_at": datetime(2025, 1, 1, 6, 0, tzinfo=UTC),
                "status": "active",
                "acknowledged_at": None,
                "cleared_at": None,
                "message": "Grid loss detected",
                "is_open": True,
                "is_critical": True,
                "acknowledgement_seconds": None,
                "resolution_seconds": None,
                "is_synthetic_ground_truth": True,
                "is_nuisance": False,
                "incident_eligible": True,
                "event_type": "grid_outage",
                "event_start_at_utc": datetime(2025, 1, 1, 6, 0, tzinfo=UTC),
                "event_end_at_utc": datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
                "generation_run_id": "RUN-TEST",
                "schema_version": "1.0.0",
            }
        ]
    )


def _incidents_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "incident_id": "INC-0000001",
                "plant_id": "PLANT-001",
                "primary_equipment_id": "EQP-00001",
                "incident_name": "Grid loss incident",
                "category": "grid_event",
                "severity": "critical",
                "priority": "p1",
                "status": "open",
                "owner_team": "grid_operations",
                "occurred_at": datetime(2025, 1, 1, 6, 0, tzinfo=UTC),
                "detected_at": datetime(2025, 1, 1, 6, 1, tzinfo=UTC),
                "assigned_at": datetime(2025, 1, 1, 6, 2, tzinfo=UTC),
                "investigation_started_at": datetime(2025, 1, 1, 6, 5, tzinfo=UTC),
                "restored_at": None,
                "resolved_at": None,
                "closed_at": None,
                "primary_alarm_id": "ALM-0000001",
                "linked_alarm_ids": ["ALM-0000001"],
                "linked_alarm_count": 1,
                "ground_truth_event_id": "GTE-2025-00000001",
                "description": "Grid loss",
                "root_cause": "Grid outage",
                "sla_response_minutes": 15,
                "sla_resolution_minutes": 480,
                "response_sla_breached": False,
                "resolution_sla_breached": False,
                "detection_seconds": 60,
                "resolution_seconds": None,
                "is_open": True,
                "is_critical": True,
                "is_synthetic_ground_truth": True,
                "generation_run_id": "RUN-TEST",
                "schema_version": "1.0.0",
            }
        ]
    )


def _work_orders_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "work_order_id": "WO-0000001",
                "linked_incident_id": "INC-0000001",
                "plant_id": "PLANT-001",
                "equipment_id": "EQP-00001",
                "work_order_name": "Inspect inverter",
                "work_order_type": "corrective",
                "priority": "critical",
                "assigned_team": "electrical_maintenance",
                "status": "open",
                "created_at": datetime(2025, 1, 1, 7, 0, tzinfo=UTC),
                "scheduled_at": None,
                "started_at": None,
                "completed_at": None,
                "cancelled_at": None,
                "estimated_labor_hours": 4.0,
                "actual_labor_hours": None,
                "estimated_cost": 500.0,
                "actual_cost": None,
                "description": "Inspect after grid loss",
                "completion_notes": None,
                "is_open": True,
                "is_over_budget": None,
                "labor_variance_hours": None,
                "cost_variance": None,
                "completion_seconds": None,
                "linked_alarm_ids": ["ALM-0000001"],
                "linked_alarm_count": 1,
                "ground_truth_event_id": "GTE-2025-00000001",
                "sla_target_hours": 24,
                "sla_breached": False,
                "is_synthetic_ground_truth": True,
                "generation_run_id": "RUN-TEST",
                "schema_version": "1.0.0",
            }
        ]
    )


def _tariffs_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "tariff_id": "TRF-0001",
                "plant_id": "PLANT-001",
                "tariff_type": "flat",
                "contract_name": "Flat tariff",
                "currency": "USD",
                "effective_start_date": date(2025, 1, 1),
                "effective_end_date": date(2025, 12, 31),
                "window_code": "ALL",
                "local_start_time": None,
                "local_end_time": None,
                "day_category": "all",
                "energy_rate_per_mwh": 80.0,
                "annual_escalation_ratio": 0.0,
                "generation_run_id": "RUN-TEST",
                "schema_version": "1.0.0",
            }
        ]
    )


def _budgets_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "budget_id": "BUD-00001",
                "plant_id": "PLANT-001",
                "budget_year": 2025,
                "budget_month": 1,
                "budget_energy_mwh": 10_000.0,
                "budget_revenue": 800_000.0,
                "target_performance_ratio": 0.82,
                "target_technical_availability_ratio": 0.98,
                "budget_opex": 50_000.0,
                "budget_planned_maintenance": 20_000.0,
                "currency": "USD",
                "basis_version": "1.0.0",
                "generation_run_id": "RUN-TEST",
                "schema_version": "1.0.0",
            }
        ]
    )


def _dataset() -> SyntheticDataset:
    """Return a small deterministic SyntheticDataset fixture."""
    jan = datetime(2025, 1, 1, 6, 0, tzinfo=UTC)
    feb = datetime(2025, 2, 1, 6, 0, tzinfo=UTC)
    return SyntheticDataset(
        plants=(_plant(),),
        equipment=(_equipment(),),
        revenue_meters=(_meter(),),
        weather=(_weather(jan), _weather(feb)),
        inverter_scada=(_scada(jan), _scada(feb)),
        plant_scada=(_plant_scada(jan), _plant_scada(feb)),
        ground_truth_events=_ground_truth_frame(),
        alarms=_alarms_frame(),
        incidents=_incidents_frame(),
        work_orders=_work_orders_frame(),
        tariffs=_tariffs_frame(),
        budgets=_budgets_frame(),
    )


def _write_full(
    tmp_path: Path,
    *,
    partition_timeseries: bool = True,
    compression: CompressionCodec = CompressionCodec.ZSTD,
    overwrite_policy: OverwritePolicy = OverwritePolicy.ERROR,
) -> tuple[SyntheticDataset, io.StagedRunDirectory, tuple[io.DatasetWriteResult, ...]]:
    """Write a full fixture dataset and return dataset, staging, and results."""
    config = GenerationConfig(
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
        output=OutputConfig(
            root=tmp_path,
            partition_timeseries=partition_timeseries,
            compression=compression,
            overwrite_policy=overwrite_policy,
        ),
    )
    dataset = _dataset()
    staging = io.StagedRunDirectory(tmp_path, "RUN-TEST-20250201")
    writer = io.DatasetWriter(config, run_id="RUN-TEST-20250201")
    results = writer.write(dataset, staging)
    return dataset, staging, results


# ---------------------------------------------------------------------------
# StagedRunDirectory tests
# ---------------------------------------------------------------------------


def test_staged_directory_creation(tmp_path: Path) -> None:
    """Creating a staged run creates the dot-staging directory."""
    staging = io.StagedRunDirectory(tmp_path, "run-test")
    staging.create()
    assert staging.staging_path.is_dir()
    assert staging.staging_path == tmp_path / ".staging" / "run-test"


def test_valid_safe_run_id(tmp_path: Path) -> None:
    """A safe run ID is accepted and normalized."""
    staging = io.StagedRunDirectory(tmp_path, "  RUN-2025-01  ")
    assert staging.run_id == "RUN-2025-01"


def test_blank_run_id_rejection(tmp_path: Path) -> None:
    """A blank run ID raises ValueError."""
    with pytest.raises(ValueError, match="blank"):
        io.StagedRunDirectory(tmp_path, "   ")


def test_path_traversal_rejection(tmp_path: Path) -> None:
    """Unsafe run IDs with traversal characters are rejected."""
    for unsafe in ("../evil", "..", ".", "a/b", "a\\b", "a b", "a*b"):
        with pytest.raises(ValueError, match="unsafe|run_id cannot be"):
            io.StagedRunDirectory(tmp_path, unsafe)


def test_existing_staging_directory_rejected(tmp_path: Path) -> None:
    """An existing staging directory raises with the default overwrite policy."""
    staging = io.StagedRunDirectory(tmp_path, "run-test")
    staging.create()
    with pytest.raises(DataGenerationError, match="already exists"):
        io.StagedRunDirectory(tmp_path, "run-test").create()


def test_existing_staging_directory_replace(tmp_path: Path) -> None:
    """OverwritePolicy.REPLACE removes an existing staging directory."""
    first = io.StagedRunDirectory(
        tmp_path,
        "run-test",
        overwrite_policy=OverwritePolicy.REPLACE,
    )
    first.create()
    (first.staging_path / "marker.txt").touch()
    second = io.StagedRunDirectory(
        tmp_path,
        "run-test",
        overwrite_policy=OverwritePolicy.REPLACE,
    )
    second.create()
    assert second.staging_path.is_dir()
    assert not (second.staging_path / "marker.txt").exists()


# ---------------------------------------------------------------------------
# Dataset writing tests
# ---------------------------------------------------------------------------


def test_writing_tuple_based_model_datasets(tmp_path: Path) -> None:
    """Tuple-based domain model datasets serialize via to_record()."""
    _, staging, results = _write_full(tmp_path)
    plants_result = next(r for r in results if r.dataset_name == "plants")
    assert plants_result.row_count == 1
    assert "plant_id" in plants_result.column_names
    assert (staging.staging_path / "master" / "plants.parquet").is_file()


def test_writing_dataframe_datasets(tmp_path: Path) -> None:
    """DataFrame datasets are written directly."""
    _, staging, results = _write_full(tmp_path)
    alarms_result = next(r for r in results if r.dataset_name == "alarms")
    assert alarms_result.row_count == 1
    assert (staging.staging_path / "operations" / "alarms.parquet").is_file()


def test_no_index_column_written(tmp_path: Path) -> None:
    """Written Parquet files contain no DataFrame index column."""
    _, _, results = _write_full(tmp_path)
    for result in results:
        for artifact in result.artifacts:
            frame = pd.read_parquet(artifact.path)
            assert "index" not in frame.columns
            assert not frame.index.name


def test_zstandard_parquet_output(tmp_path: Path) -> None:
    """Parquet output uses Zstandard compression by default."""
    _, _, results = _write_full(tmp_path)
    plants_result = next(r for r in results if r.dataset_name == "plants")
    file_path = plants_result.artifacts[0].path
    parquet_file = pq.ParquetFile(file_path)
    assert parquet_file.metadata.num_rows == 1
    for row_group_index in range(parquet_file.metadata.num_row_groups):
        row_group = parquet_file.metadata.row_group(row_group_index)
        for column_index in range(row_group.num_columns):
            assert row_group.column(column_index).compression == "ZSTD"


def test_gzip_compression_output(tmp_path: Path) -> None:
    """GZip compression is honored from OutputConfig."""
    _, _, results = _write_full(tmp_path, compression=CompressionCodec.GZIP)
    plants_result = next(r for r in results if r.dataset_name == "plants")
    file_path = plants_result.artifacts[0].path
    parquet_file = pq.ParquetFile(file_path)
    for row_group_index in range(parquet_file.metadata.num_row_groups):
        row_group = parquet_file.metadata.row_group(row_group_index)
        for column_index in range(row_group.num_columns):
            assert row_group.column(column_index).compression == "GZIP"


def test_stable_column_ordering(tmp_path: Path) -> None:
    """Written columns preserve the source DataFrame column order."""
    _, _, results = _write_full(tmp_path)
    dataset = _dataset()
    expected_columns = tuple(_dataset_columns(dataset, "plants"))
    plants_result = next(r for r in results if r.dataset_name == "plants")
    assert plants_result.column_names == expected_columns


def _dataset_columns(dataset: SyntheticDataset, name: str) -> list[str]:
    """Return the prepared column names the writer would produce."""
    value = getattr(dataset, name)
    if isinstance(value, pd.DataFrame):
        cols = list(value.columns)
    else:
        cols = list(value[0].to_record().keys())
    if "generation_run_id" not in cols:
        cols.append("generation_run_id")
    if "schema_version" not in cols:
        cols.append("schema_version")
    return cols


def test_timezone_aware_timestamps_preserved(tmp_path: Path) -> None:
    """UTC-aware timestamps survive the Parquet round trip."""
    _, _, results = _write_full(tmp_path)
    weather_result = next(r for r in results if r.dataset_name == "weather")
    read_back = pd.read_parquet(weather_result.artifacts[0].path)
    timestamps = pd.to_datetime(read_back["timestamp"], utc=True)
    assert timestamps.dt.tz is not None
    assert timestamps.dt.tz.utcoffset(None) == pd.Timedelta(0)


def test_deterministic_filenames(tmp_path: Path) -> None:
    """Non-partitioned files use deterministic part-00000.parquet names."""
    _, _, results = _write_full(tmp_path, partition_timeseries=False)
    for result in results:
        for relative_path in result.relative_paths:
            assert relative_path.name == "part-00000.parquet" or (
                relative_path.suffix == ".parquet"
            )


def test_empty_dataset_behavior(tmp_path: Path) -> None:
    """Empty DataFrames produce zero-row Parquet files without errors."""
    config = _config(tmp_path)
    staging = io.StagedRunDirectory(tmp_path, "run-empty")
    dataset = SyntheticDataset(
        plants=(_plant(),),
        equipment=(_equipment(),),
        revenue_meters=(_meter(),),
        weather=(_weather(datetime(2025, 1, 1, 6, 0, tzinfo=UTC)),),
        inverter_scada=(_scada(datetime(2025, 1, 1, 6, 0, tzinfo=UTC)),),
        plant_scada=(_plant_scada(datetime(2025, 1, 1, 6, 0, tzinfo=UTC)),),
        ground_truth_events=pd.DataFrame(
            columns=[
                "ground_truth_event_id",
                "event_type",
                "start_at_utc",
                "generation_run_id",
                "schema_version",
            ]
        ),
        alarms=pd.DataFrame(
            columns=[
                "alarm_id",
                "raised_at",
                "generation_run_id",
                "schema_version",
            ]
        ),
        incidents=pd.DataFrame(
            columns=[
                "incident_id",
                "occurred_at",
                "generation_run_id",
                "schema_version",
            ]
        ),
        work_orders=pd.DataFrame(
            columns=[
                "work_order_id",
                "created_at",
                "generation_run_id",
                "schema_version",
            ]
        ),
        tariffs=pd.DataFrame(
            columns=["tariff_id", "generation_run_id", "schema_version"]
        ),
        budgets=pd.DataFrame(
            columns=["budget_id", "generation_run_id", "schema_version"]
        ),
    )
    writer = io.DatasetWriter(config, run_id="run-empty")
    results = writer.write(dataset, staging)
    alarms_result = next(r for r in results if r.dataset_name == "alarms")
    assert alarms_result.row_count == 0
    assert alarms_result.file_count == 1
    assert pd.read_parquet(alarms_result.artifacts[0].path).empty


def test_partitioned_weather_output(tmp_path: Path) -> None:
    """Weather is partitioned by year/month when configured."""
    _, staging, results = _write_full(tmp_path)
    weather_result = next(r for r in results if r.dataset_name == "weather")
    assert weather_result.file_count >= 2
    parquet_files = sorted(
        (staging.staging_path / "timeseries" / "weather").rglob("*.parquet")
    )
    assert len(parquet_files) == 2
    for file_path in parquet_files:
        relative = file_path.relative_to(
            staging.staging_path / "timeseries" / "weather"
        )
        parts = [part for part in relative.parts if "=" in part]
        assert any(part.startswith("year=") for part in parts)
        assert any(part.startswith("month=") for part in parts)


def test_partitioned_inverter_scada_output(tmp_path: Path) -> None:
    """Inverter SCADA is partitioned by year/month/plant_id when configured."""
    _, staging, results = _write_full(tmp_path)
    scada_result = next(r for r in results if r.dataset_name == "inverter_scada")
    assert scada_result.file_count >= 2
    base_dir = staging.staging_path / "timeseries" / "inverter_scada"
    for file_path in sorted(base_dir.rglob("*.parquet")):
        assert file_path.name.startswith("part-")
        assert len(file_path.name) <= len("part-00000.parquet")
        relative = file_path.relative_to(base_dir)
        parts = [part for part in relative.parts if "=" in part]
        assert any(part.startswith("year=") for part in parts)
        assert any(part.startswith("month=") for part in parts)
        assert any(part.startswith("plant_id=") for part in parts)


def test_non_partitioned_output_option(tmp_path: Path) -> None:
    """partition_timeseries=False writes single Parquet files."""
    _, staging, results = _write_full(tmp_path, partition_timeseries=False)
    weather_result = next(r for r in results if r.dataset_name == "weather")
    assert weather_result.file_count == 1
    assert (staging.staging_path / "timeseries" / "weather.parquet").is_file()


def test_master_operations_commercial_not_partitioned(tmp_path: Path) -> None:
    """Master, operations, commercial, and truth files are not partitioned."""
    _, staging, results = _write_full(tmp_path)
    for result in results:
        if result.family in {"master", "operations", "commercial", "truth"}:
            assert result.file_count == 1
            assert (
                staging.staging_path / result.family / f"{result.dataset_name}.parquet"
            ).is_file()


# ---------------------------------------------------------------------------
# read_dataset tests
# ---------------------------------------------------------------------------


def test_read_dataset_round_trip(tmp_path: Path) -> None:
    """read_dataset reads back a non-partitioned Parquet file."""
    _, staging, results = _write_full(tmp_path, partition_timeseries=False)
    plants_path = staging.staging_path / "master" / "plants.parquet"
    frame = io.read_dataset(plants_path)
    assert len(frame) == 1
    assert "plant_id" in frame.columns


def test_read_dataset_partitioned(tmp_path: Path) -> None:
    """read_dataset reads back a partitioned Parquet directory."""
    _, staging, results = _write_full(tmp_path)
    weather_dir = staging.staging_path / "timeseries" / "weather"
    frame = io.read_dataset(weather_dir)
    assert len(frame) == 2
    assert "timestamp" in frame.columns


def test_read_dataset_missing_path(tmp_path: Path) -> None:
    """read_dataset raises DataGenerationError for a missing path."""
    with pytest.raises(DataGenerationError, match="does not exist"):
        io.read_dataset(tmp_path / "missing" / "file.parquet")


# ---------------------------------------------------------------------------
# Structured write-result metadata tests
# ---------------------------------------------------------------------------


def test_structured_write_result_metadata(tmp_path: Path) -> None:
    """DatasetWriteResult reports all required structured metadata."""
    _, _, results = _write_full(tmp_path)
    weather_result = next(r for r in results if r.dataset_name == "weather")
    assert isinstance(weather_result, io.DatasetWriteResult)
    assert weather_result.dataset_name == "weather"
    assert weather_result.family == "timeseries"
    assert weather_result.row_count == 2
    assert weather_result.file_count == 2
    assert weather_result.total_bytes > 0
    assert "timestamp" in weather_result.column_names
    assert weather_result.min_timestamp is not None
    assert weather_result.max_timestamp is not None
    assert weather_result.min_timestamp == datetime(2025, 1, 1, 6, 0, tzinfo=UTC)
    assert weather_result.max_timestamp == datetime(2025, 2, 1, 6, 0, tzinfo=UTC)
    assert all(isinstance(a, io.DatasetArtifact) for a in weather_result.artifacts)
    assert all(a.byte_size > 0 for a in weather_result.artifacts)


def test_audit_columns_added(tmp_path: Path) -> None:
    """Audit columns are added to datasets that lack them."""
    _, _, results = _write_full(tmp_path)
    plants_result = next(r for r in results if r.dataset_name == "plants")
    assert "generation_run_id" in plants_result.column_names
    assert "schema_version" in plants_result.column_names
    # Master datasets are not fact datasets; source_system is only for facts.
    assert "source_system" not in plants_result.column_names
    weather_result = next(r for r in results if r.dataset_name == "weather")
    assert "source_system" in weather_result.column_names


def test_audit_columns_not_duplicated(tmp_path: Path) -> None:
    """Existing audit columns on DataFrame datasets are not duplicated."""
    _, _, results = _write_full(tmp_path)
    alarms_result = next(r for r in results if r.dataset_name == "alarms")
    assert alarms_result.column_names.count("generation_run_id") == 1
    assert alarms_result.column_names.count("schema_version") == 1


# ---------------------------------------------------------------------------
# Atomic publication tests
# ---------------------------------------------------------------------------


def test_atomic_publication(tmp_path: Path) -> None:
    """A completed staging run is atomically published to runs/."""
    _, staging, _ = _write_full(tmp_path)
    published = io.publish_run(staging)
    assert published == tmp_path / "runs" / "RUN-TEST-20250201"
    assert published.is_dir()
    assert (published / "master" / "plants.parquet").is_file()
    assert not staging.staging_path.exists()


def test_publication_rejects_existing_final_run(tmp_path: Path) -> None:
    """Publication rejects an existing final run under the default policy."""
    _, staging, _ = _write_full(tmp_path)
    io.publish_run(staging)
    # Attempt a second publication to the same final path under the same root.
    second = io.StagedRunDirectory(tmp_path, "RUN-TEST-20250201")
    second.create()
    with pytest.raises(DataGenerationError, match="already exists"):
        second.publish()


def test_publish_requires_staging_directory(tmp_path: Path) -> None:
    """Publishing without a staging directory raises."""
    staging = io.StagedRunDirectory(tmp_path, "run-not-created")
    with pytest.raises(DataGenerationError, match="does not exist"):
        staging.publish()


def test_context_manager_does_not_publish_after_exception(tmp_path: Path) -> None:
    """A context-managed staging directory cleans up on exception."""
    with (
        pytest.raises(RuntimeError),
        io.StagedRunDirectory(tmp_path, "run-fail") as staging,
    ):
        assert staging.staging_path.is_dir()
        raise RuntimeError("boom")
    assert not staging.staging_path.exists()
    assert not (tmp_path / "runs" / "run-fail").exists()


def test_context_manager_publish_manual(tmp_path: Path) -> None:
    """A context manager alone does not auto-publish on clean exit."""
    with io.StagedRunDirectory(tmp_path, "run-ok") as staging:
        staging.staging_path.mkdir(parents=True, exist_ok=True)
    assert staging.staging_path.is_dir()
    assert not (tmp_path / "runs" / "run-ok").exists()


# ---------------------------------------------------------------------------
# Determinism and immutability tests
# ---------------------------------------------------------------------------


def test_source_dataset_not_mutated(tmp_path: Path) -> None:
    """Writing does not mutate the source dataset tuples or DataFrames."""
    dataset = _dataset()
    original_plants = tuple(dataset.plants)
    original_weather = tuple(dataset.weather)
    original_alarms = dataset.alarms.copy(deep=True)

    _, _, _ = _write_full(tmp_path)

    assert dataset.plants == original_plants
    assert dataset.weather == original_weather
    assert dataset.alarms.equals(original_alarms)


def test_deterministic_run_id(tmp_path: Path) -> None:
    """The derived run ID is deterministic from configuration."""
    config = _config(tmp_path)
    writer_a = io.DatasetWriter(config)
    writer_b = io.DatasetWriter(config)
    assert writer_a.run_id == writer_b.run_id
    assert writer_a.run_id == "RUN-20250101T000000Z-20250201"


# ---------------------------------------------------------------------------
# Error-handling tests
# ---------------------------------------------------------------------------


def test_invalid_input_type(tmp_path: Path) -> None:
    """write() rejects non-SyntheticDataset input."""
    config = _config(tmp_path)
    staging = io.StagedRunDirectory(tmp_path, "run-test")
    writer = io.DatasetWriter(config)
    with pytest.raises(TypeError, match="SyntheticDataset"):
        writer.write("not-a-dataset", staging)  # type: ignore[arg-type]


def test_missing_parquet_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing pyarrow dependency raises a clear EOIP error."""
    config = _config(tmp_path)

    def raise_missing() -> None:
        raise DataGenerationError(
            "Parquet output requires the 'pyarrow' package. "
            "Install it with: python -m pip install pyarrow"
        )

    monkeypatch.setattr(io, "_check_parquet_dependency", raise_missing)
    with pytest.raises(DataGenerationError, match="pyarrow"):
        io.DatasetWriter(config)


def test_filesystem_failure_wrapping(tmp_path: Path) -> None:
    """Filesystem failures are wrapped with operation and target context."""
    config = _config(tmp_path)
    staging = io.StagedRunDirectory(tmp_path, "run-test").create()
    # Make the master family directory a file so writing plants fails.
    (staging.staging_path / "master").write_text("not a directory")
    writer = io.DatasetWriter(config)
    with pytest.raises(DataGenerationError, match="plants"):
        writer.write(_dataset(), staging)


def test_invalid_staging_type(tmp_path: Path) -> None:
    """write() rejects non-StagedRunDirectory staging input."""
    config = _config(tmp_path)
    writer = io.DatasetWriter(config)
    with pytest.raises(TypeError, match="StagedRunDirectory"):
        writer.write(_dataset(), "not-staging")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# latest_pointer tests
# ---------------------------------------------------------------------------


def test_latest_pointer_none_when_no_runs(tmp_path: Path) -> None:
    """latest_pointer returns None when no runs exist."""
    assert io.latest_pointer(tmp_path) is None


def test_latest_pointer_returns_most_recent(tmp_path: Path) -> None:
    """latest_pointer returns the most recently published run directory."""
    first = io.StagedRunDirectory(tmp_path, "run-a").create()
    first.publish()
    second = io.StagedRunDirectory(tmp_path, "run-b").create()
    second.publish()
    latest = io.latest_pointer(tmp_path)
    assert latest is not None
    assert latest.name == "run-b"
