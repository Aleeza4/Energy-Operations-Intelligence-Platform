"""In-memory master dataset assembler for EOIP Phase 2 synthetic generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

import numpy as np
import pandas as pd

from eoip.core.exceptions import DataGenerationError
from eoip.synthetic.config import GenerationConfig
from eoip.synthetic.events.catalogue import EventScope
from eoip.synthetic.events.effects import (
    EffectApplicationConfig,
    apply_inverter_scada_events,
    apply_plant_scada_events,
    apply_weather_events,
)
from eoip.synthetic.events.scheduler import (
    EligibleAsset,
    EventSchedulerConfig,
    SyntheticEvent,
    events_to_frame,
    schedule_events,
)
from eoip.synthetic.generators import (
    EquipmentGeneratorConfig,
    MeterGeneratorConfig,
    PlantGeneratorConfig,
    PlantSCADAGeneratorConfig,
    SCADAGeneratorConfig,
    generate_equipment,
    generate_plant_scada,
    generate_plants,
    generate_revenue_meters,
    generate_scada,
)
from eoip.synthetic.generators.budgets import (
    BudgetGeneratorConfig,
    generate_budgets,
)
from eoip.synthetic.generators.tariffs import (
    TariffGeneratorConfig,
    generate_tariffs,
)
from eoip.synthetic.generators.weather_generator import (
    WeatherGeneratorConfig,
    generate_weather,
)
from eoip.synthetic.models.equipment import Equipment, EquipmentType
from eoip.synthetic.models.meter import RevenueMeter
from eoip.synthetic.models.plant import Plant
from eoip.synthetic.models.plant_scada import PlantSCADAObservation
from eoip.synthetic.models.scada import SCADAObservation
from eoip.synthetic.models.weather import WeatherObservation
from eoip.synthetic.operations.alarms import (
    AlarmOperationsConfig,
    AlarmSCADAContext,
    generate_alarms,
)
from eoip.synthetic.operations.incidents import (
    IncidentOperationsConfig,
    generate_incidents,
)
from eoip.synthetic.operations.work_orders import (
    WorkOrderOperationsConfig,
    generate_work_orders,
)
from eoip.synthetic.random import RandomContext, create_random_context

_DEFAULT_RUN_PREFIX: Final[str] = "RUN"


class _RandomContextAdapter:
    """Bridge RandomContext to the generator(name, entity_id) protocol."""

    __slots__ = ("_context", "_stream_name_map")

    _OPERATIONS_STREAM_MAP: Final[dict[str, str]] = {
        "operations.alarms": "alarms",
        "operations.alarms.nuisance": "alarms",
        "operations.incidents": "incidents",
        "operations.work_orders": "work_orders",
    }

    def __init__(self, context: RandomContext) -> None:
        self._context = context
        self._stream_name_map = dict(self._OPERATIONS_STREAM_MAP)

    def generator(
        self,
        name: str,
        entity_id: str | None = None,
    ) -> np.random.Generator:
        stream_name = self._stream_name_map.get(name, name)
        if entity_id is None:
            return self._context.stream(stream_name)
        return self._context.entity_stream(stream_name, entity_id)


@dataclass(frozen=True, slots=True)
class SyntheticDataset:
    """Immutable in-memory master dataset assembled by the generator."""

    plants: tuple[Plant, ...]
    equipment: tuple[Equipment, ...]
    revenue_meters: tuple[RevenueMeter, ...]
    weather: tuple[WeatherObservation, ...]
    inverter_scada: tuple[SCADAObservation, ...]
    plant_scada: tuple[PlantSCADAObservation, ...]
    ground_truth_events: pd.DataFrame
    alarms: pd.DataFrame
    incidents: pd.DataFrame
    work_orders: pd.DataFrame
    tariffs: pd.DataFrame
    budgets: pd.DataFrame

    def __post_init__(self) -> None:
        for name, value in (
            ("plants", self.plants),
            ("equipment", self.equipment),
            ("revenue_meters", self.revenue_meters),
            ("weather", self.weather),
            ("inverter_scada", self.inverter_scada),
            ("plant_scada", self.plant_scada),
        ):
            if not isinstance(value, tuple):
                raise TypeError(f"{name} must be a tuple.")
        for name, frame in (
            ("ground_truth_events", self.ground_truth_events),
            ("alarms", self.alarms),
            ("incidents", self.incidents),
            ("work_orders", self.work_orders),
            ("tariffs", self.tariffs),
            ("budgets", self.budgets),
        ):
            if not isinstance(frame, pd.DataFrame):
                raise TypeError(f"{name} must be a pandas DataFrame.")


@dataclass(frozen=True, slots=True)
class GenerationSummary:
    """Row counts and metadata for one generation run."""

    plant_count: int
    equipment_count: int
    revenue_meter_count: int
    weather_count: int
    inverter_scada_count: int
    plant_scada_count: int
    ground_truth_event_count: int
    alarm_count: int
    incident_count: int
    work_order_count: int
    tariff_count: int
    budget_count: int
    generation_run_id: str

    def to_record(self) -> dict[str, int | str]:
        return {
            "plant_count": self.plant_count,
            "equipment_count": self.equipment_count,
            "revenue_meter_count": self.revenue_meter_count,
            "weather_count": self.weather_count,
            "inverter_scada_count": self.inverter_scada_count,
            "plant_scada_count": self.plant_scada_count,
            "ground_truth_event_count": self.ground_truth_event_count,
            "alarm_count": self.alarm_count,
            "incident_count": self.incident_count,
            "work_order_count": self.work_order_count,
            "tariff_count": self.tariff_count,
            "budget_count": self.budget_count,
            "generation_run_id": self.generation_run_id,
        }


class SyntheticDatasetGenerator:
    """Deterministic in-memory master dataset assembler."""

    def __init__(
        self,
        config: GenerationConfig,
        random_context: RandomContext | None = None,
    ) -> None:
        if not isinstance(config, GenerationConfig):
            raise TypeError("config must be a GenerationConfig.")
        self._config = config
        self._random_context = random_context or create_random_context(config.seed)
        self._adapter = _RandomContextAdapter(self._random_context)
        self._generation_run_id = _build_run_id(config)

    @property
    def config(self) -> GenerationConfig:
        return self._config

    @property
    def random_context(self) -> RandomContext:
        return self._random_context

    @property
    def generation_run_id(self) -> str:
        return self._generation_run_id

    def generate(self) -> SyntheticDataset:
        try:
            return self._generate_internal()
        except (TypeError, ValueError, KeyError) as exc:
            raise DataGenerationError(
                f"Synthetic dataset generation failed: {exc}"
            ) from exc

    def _generate_internal(self) -> SyntheticDataset:
        plants = self._generate_plants()
        equipment = self._generate_equipment(plants)
        revenue_meters = self._generate_revenue_meters(plants, equipment)
        self._validate_master_references(plants, equipment, revenue_meters)

        weather = self._generate_weather(plants, equipment)
        time_grid = self._build_time_grid()
        events = self._schedule_events(plants, equipment, time_grid)

        weather_frame = self._weather_to_frame(weather)
        weather_result = apply_weather_events(
            weather_frame, events, config=EffectApplicationConfig()
        )
        weather_frame = weather_result.frame

        inverter_scada = self._generate_inverter_scada(plants, equipment, weather)
        inverter_frame = self._inverter_scada_to_frame(inverter_scada)
        inverter_result = apply_inverter_scada_events(
            inverter_frame, events, config=EffectApplicationConfig()
        )
        inverter_frame = inverter_result.frame

        plant_scada = self._generate_plant_scada(
            plants, equipment, revenue_meters, inverter_scada
        )
        plant_frame = self._plant_scada_to_frame(plant_scada)
        plant_result = apply_plant_scada_events(
            plant_frame, events, config=EffectApplicationConfig()
        )
        plant_frame = plant_result.frame

        ground_truth_frame = events_to_frame(events)
        alarms = self._generate_alarms(events, plants, equipment)
        incidents = self._generate_incidents(alarms)
        work_orders = self._generate_work_orders(incidents)
        tariffs = self._generate_tariffs(plants)
        budgets = self._generate_budgets(plants, tariffs)

        self._validate_referential_integrity(
            plants,
            equipment,
            revenue_meters,
            weather,
            inverter_scada,
            plant_scada,
            ground_truth_frame,
            alarms,
            incidents,
            work_orders,
        )

        return SyntheticDataset(
            plants=plants,
            equipment=equipment,
            revenue_meters=revenue_meters,
            weather=weather,
            inverter_scada=inverter_scada,
            plant_scada=plant_scada,
            ground_truth_events=ground_truth_frame,
            alarms=alarms,
            incidents=incidents,
            work_orders=work_orders,
            tariffs=tariffs,
            budgets=budgets,
        )

    def summarize(self, dataset: SyntheticDataset) -> GenerationSummary:
        return GenerationSummary(
            plant_count=len(dataset.plants),
            equipment_count=len(dataset.equipment),
            revenue_meter_count=len(dataset.revenue_meters),
            weather_count=len(dataset.weather),
            inverter_scada_count=len(dataset.inverter_scada),
            plant_scada_count=len(dataset.plant_scada),
            ground_truth_event_count=len(dataset.ground_truth_events),
            alarm_count=len(dataset.alarms),
            incident_count=len(dataset.incidents),
            work_order_count=len(dataset.work_orders),
            tariff_count=len(dataset.tariffs),
            budget_count=len(dataset.budgets),
            generation_run_id=self._generation_run_id,
        )

    def _plant_config(self) -> PlantGeneratorConfig:
        return PlantGeneratorConfig(
            plant_count=self._config.portfolio.plant_count,
            random_seed=self._config.seed,
        )

    def _equipment_config(self) -> EquipmentGeneratorConfig:
        return EquipmentGeneratorConfig(random_seed=self._config.seed)

    def _weather_config(self) -> WeatherGeneratorConfig:
        return WeatherGeneratorConfig(
            start_at=self._config.time.start,
            duration_days=int(self._config.time.duration_days),
            interval_minutes=self._config.time.interval_minutes,
            random_seed=self._config.seed,
        )

    def _scada_config(self) -> SCADAGeneratorConfig:
        return SCADAGeneratorConfig(
            start_at=self._config.time.start,
            duration_days=int(self._config.time.duration_days),
            interval_minutes=self._config.time.interval_minutes,
            random_seed=self._config.seed,
        )

    def _generate_plants(self) -> tuple[Plant, ...]:
        return generate_plants(self._plant_config())

    def _generate_equipment(self, plants: tuple[Plant, ...]) -> tuple[Equipment, ...]:
        return generate_equipment(
            self._equipment_config(), plant_config=self._plant_config()
        )

    def _generate_revenue_meters(
        self,
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
    ) -> tuple[RevenueMeter, ...]:
        return generate_revenue_meters(
            MeterGeneratorConfig(random_seed=self._config.seed),
            plant_config=self._plant_config(),
            equipment_config=self._equipment_config(),
        )

    def _generate_weather(
        self,
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
    ) -> tuple[WeatherObservation, ...]:
        return generate_weather(
            self._weather_config(),
            plant_config=self._plant_config(),
            equipment_config=self._equipment_config(),
        )

    def _generate_inverter_scada(
        self,
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
        weather: tuple[WeatherObservation, ...],
    ) -> tuple[SCADAObservation, ...]:
        return generate_scada(
            self._scada_config(),
            plant_config=self._plant_config(),
            equipment_config=self._equipment_config(),
            weather_config=self._weather_config(),
        )

    def _generate_plant_scada(
        self,
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
        revenue_meters: tuple[RevenueMeter, ...],
        inverter_scada: tuple[SCADAObservation, ...],
    ) -> tuple[PlantSCADAObservation, ...]:
        return generate_plant_scada(
            PlantSCADAGeneratorConfig(),
            scada_config=self._scada_config(),
            plant_config=self._plant_config(),
            equipment_config=self._equipment_config(),
            weather_config=self._weather_config(),
            meter_config=MeterGeneratorConfig(random_seed=self._config.seed),
            inverter_observations=inverter_scada,
        )

    def _schedule_events(
        self,
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
        time_grid: tuple[datetime, ...],
    ) -> tuple[SyntheticEvent, ...]:
        portfolio = self._build_portfolio(plants, equipment)
        scheduler_config = EventSchedulerConfig(
            random_seed=self._config.seed,
            interval_minutes=self._config.time.interval_minutes,
            rate_multiplier=self._config.events.annual_event_rate_multiplier,
        )
        return schedule_events(
            portfolio,
            time_grid,
            config=scheduler_config,
            random_context=self._adapter,
            generation_run_id=self._generation_run_id,
        )

    def _generate_alarms(
        self,
        events: tuple[SyntheticEvent, ...],
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
    ) -> pd.DataFrame:
        scada_context = self._build_alarm_scada_context(plants, equipment)
        return generate_alarms(
            events,
            scada_context=scada_context,
            config=AlarmOperationsConfig(random_seed=self._config.seed),
            random_context=self._adapter,
        )

    def _generate_incidents(self, alarms: pd.DataFrame) -> pd.DataFrame:
        return generate_incidents(
            alarms,
            config=IncidentOperationsConfig(random_seed=self._config.seed),
            random_context=self._adapter,
        )

    def _generate_work_orders(self, incidents: pd.DataFrame) -> pd.DataFrame:
        return generate_work_orders(
            incidents,
            config=WorkOrderOperationsConfig(random_seed=self._config.seed),
            random_context=self._adapter,
        )

    def _generate_tariffs(self, plants: tuple[Plant, ...]) -> pd.DataFrame:
        return generate_tariffs(
            self._plants_to_frame(plants),
            self._config.time,
            config=TariffGeneratorConfig(random_seed=self._config.seed),
            random_context=self._adapter,
            generation_run_id=self._generation_run_id,
        )

    def _generate_budgets(
        self,
        plants: tuple[Plant, ...],
        tariffs: pd.DataFrame,
    ) -> pd.DataFrame:
        return generate_budgets(
            self._plants_to_frame(plants),
            None,
            tariffs,
            self._build_month_windows(),
            config=BudgetGeneratorConfig(random_seed=self._config.seed),
            random_context=self._adapter,
            generation_run_id=self._generation_run_id,
        )

    def _build_time_grid(self) -> tuple[datetime, ...]:
        start = self._config.time.start
        end = self._config.time.end
        interval = timedelta(minutes=self._config.time.interval_minutes)
        timestamps: list[datetime] = []
        current = start
        while current < end:
            timestamps.append(current)
            current += interval
        return tuple(timestamps)

    def _build_portfolio(
        self,
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
    ) -> tuple[EligibleAsset, ...]:
        assets: list[EligibleAsset] = []
        for plant in plants:
            assets.append(
                EligibleAsset(
                    scope=EventScope.PLANT,
                    plant_id=plant.plant_id,
                    asset_type="plant",
                    asset_id=plant.plant_id,
                )
            )
        scope_by_type = {
            EquipmentType.STRING_INVERTER: EventScope.INVERTER,
            EquipmentType.CENTRAL_INVERTER: EventScope.INVERTER,
            EquipmentType.TRANSFORMER: EventScope.TRANSFORMER,
            EquipmentType.FEEDER: EventScope.FEEDER,
            EquipmentType.WEATHER_STATION: EventScope.SENSOR,
            EquipmentType.REVENUE_METER: EventScope.SENSOR,
        }
        for item in equipment:
            scope = scope_by_type.get(item.equipment_type)
            if scope is None:
                continue
            assets.append(
                EligibleAsset(
                    scope=scope,
                    plant_id=item.plant_id,
                    asset_type=item.equipment_type.value,
                    asset_id=item.equipment_id,
                )
            )
        return tuple(assets)

    def _build_alarm_scada_context(
        self,
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
    ) -> AlarmSCADAContext:
        equipment_id_by_asset = {
            item.equipment_id: item.equipment_id for item in equipment
        }
        default_equipment_id_by_plant: dict[str, str] = {}
        for plant in plants:
            plant_equipment = tuple(
                item for item in equipment if item.plant_id == plant.plant_id
            )
            if plant_equipment:
                default_equipment_id_by_plant[plant.plant_id] = plant_equipment[
                    0
                ].equipment_id
        return AlarmSCADAContext(
            equipment_id_by_asset=equipment_id_by_asset,
            default_equipment_id_by_plant=default_equipment_id_by_plant,
            observation_end_at=self._config.time.end,
        )

    def _build_month_windows(self) -> list[datetime]:
        start = self._config.time.start
        end = self._config.time.end
        months: list[datetime] = []
        current = datetime(start.year, start.month, 1, tzinfo=UTC)
        while current < end:
            months.append(current)
            if current.month == 12:
                current = datetime(current.year + 1, 1, 1, tzinfo=UTC)
            else:
                current = datetime(current.year, current.month + 1, 1, tzinfo=UTC)
        return months

    def _plants_to_frame(self, plants: tuple[Plant, ...]) -> pd.DataFrame:
        return pd.DataFrame.from_records([plant.to_record() for plant in plants])

    def _weather_to_frame(
        self,
        weather: tuple[WeatherObservation, ...],
    ) -> pd.DataFrame:
        records = []
        for observation in weather:
            record = observation.to_record()
            records.append(
                {
                    "timestamp_utc": record.get("timestamp", observation.timestamp),
                    "weather_station_id": record.get(
                        "weather_station_id", observation.weather_station_id
                    ),
                    "plant_id": record.get("plant_id", observation.plant_id),
                    "ghi_w_m2": record.get("ghi_wm2", observation.ghi_wm2),
                    "dni_w_m2": record.get("dni_wm2", observation.dni_wm2),
                    "dhi_w_m2": record.get("dhi_wm2", observation.dhi_wm2),
                    "poa_irradiance_w_m2": 0.0,
                    "ambient_temperature_c": record.get(
                        "ambient_temperature_c", observation.ambient_temperature_c
                    ),
                    "cell_temperature_c": record.get(
                        "module_temperature_c", observation.module_temperature_c
                    ),
                    "wind_speed_m_s": record.get(
                        "wind_speed_ms", observation.wind_speed_ms
                    ),
                    "relative_humidity_pct": record.get(
                        "relative_humidity_pct", observation.relative_humidity_pct
                    ),
                    "precipitation_mm": 0.0,
                    "atmospheric_pressure_hpa": 1_013.25,
                    "quality_flag": record.get("quality", observation.quality.value),
                    "ground_truth_event_id": pd.NA,
                }
            )
        return pd.DataFrame.from_records(records)

    def _inverter_scada_to_frame(
        self,
        observations: tuple[SCADAObservation, ...],
    ) -> pd.DataFrame:
        records = []
        for observation in observations:
            record = observation.to_record()
            records.append(
                {
                    "timestamp_utc": record.get("timestamp", observation.timestamp),
                    "inverter_id": record.get("equipment_id", observation.equipment_id),
                    "plant_id": record.get("plant_id", observation.plant_id),
                    "feeder_id": pd.NA,
                    "transformer_id": pd.NA,
                    "operating_state": record.get(
                        "operating_state", observation.operating_state.value
                    ),
                    "availability_ratio": 1.0,
                    "expected_dc_power_kw": 0.0,
                    "dc_power_kw": 0.0,
                    "dc_voltage_v": record.get(
                        "dc_voltage_v", observation.dc_voltage_v
                    ),
                    "dc_current_a": record.get(
                        "dc_current_a", observation.dc_current_a
                    ),
                    "expected_ac_power_kw": 0.0,
                    "ac_power_kw": record.get(
                        "active_power_kw", observation.active_power_kw
                    ),
                    "ac_voltage_v": record.get(
                        "ac_voltage_v", observation.ac_voltage_v
                    ),
                    "ac_current_a": record.get(
                        "ac_current_a", observation.ac_current_a
                    ),
                    "reactive_power_kvar": 0.0,
                    "apparent_power_kva": 0.0,
                    "power_factor": record.get(
                        "power_factor", observation.power_factor
                    ),
                    "frequency_hz": record.get(
                        "frequency_hz", observation.frequency_hz
                    ),
                    "inverter_temperature_c": 25.0,
                    "conversion_efficiency_ratio": 0.975,
                    "interval_energy_kwh": record.get(
                        "interval_energy_kwh", observation.interval_energy_kwh
                    ),
                    "quality_flag": record.get("quality", observation.quality.value),
                    "ground_truth_event_id": pd.NA,
                }
            )
        return pd.DataFrame.from_records(records)

    def _plant_scada_to_frame(
        self,
        observations: tuple[PlantSCADAObservation, ...],
    ) -> pd.DataFrame:
        records = []
        for observation in observations:
            record = observation.to_record()
            records.append(
                {
                    "timestamp_utc": record.get("timestamp", observation.timestamp),
                    "plant_id": record.get("plant_id", observation.plant_id),
                    "meter_id": record.get("meter_id", observation.meter_id),
                    "available_capacity_mw": 0.0,
                    "expected_power_mw": 0.0,
                    "gross_inverter_power_mw": record.get(
                        "gross_inverter_power_kw", observation.gross_inverter_power_kw
                    )
                    / 1_000.0,
                    "transformer_loss_mw": record.get(
                        "transformer_loss_kw", observation.transformer_loss_kw
                    )
                    / 1_000.0,
                    "collection_loss_mw": record.get(
                        "collection_loss_kw", observation.collection_loss_kw
                    )
                    / 1_000.0,
                    "curtailment_loss_mw": 0.0,
                    "export_power_mw": record.get(
                        "export_power_kw", observation.export_power_kw
                    )
                    / 1_000.0,
                    "import_power_mw": record.get(
                        "import_power_kw", observation.import_power_kw
                    )
                    / 1_000.0,
                    "reactive_power_mvar": 0.0,
                    "power_factor": 0.99,
                    "grid_frequency_hz": 50.0,
                    "interval_export_energy_mwh": record.get(
                        "interval_export_energy_kwh",
                        observation.interval_export_energy_kwh,
                    )
                    / 1_000.0,
                    "cumulative_export_energy_mwh": record.get(
                        "cumulative_export_energy_kwh",
                        observation.cumulative_export_energy_kwh,
                    )
                    / 1_000.0,
                    "interval_import_energy_mwh": record.get(
                        "interval_import_energy_kwh",
                        observation.interval_import_energy_kwh,
                    )
                    / 1_000.0,
                    "quality_flag": record.get("quality", observation.quality.value),
                    "ground_truth_event_id": pd.NA,
                }
            )
        return pd.DataFrame.from_records(records)

    def _validate_master_references(
        self,
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
        revenue_meters: tuple[RevenueMeter, ...],
    ) -> None:
        plant_ids = {plant.plant_id for plant in plants}
        unknown_equipment_plants = {item.plant_id for item in equipment} - plant_ids
        if unknown_equipment_plants:
            raise DataGenerationError(
                "Equipment references unknown plant IDs: "
                + ", ".join(sorted(unknown_equipment_plants))
            )
        unknown_meter_plants = {meter.plant_id for meter in revenue_meters} - plant_ids
        if unknown_meter_plants:
            raise DataGenerationError(
                "Revenue meters reference unknown plant IDs: "
                + ", ".join(sorted(unknown_meter_plants))
            )
        meter_counts: dict[str, int] = {}
        for meter in revenue_meters:
            meter_counts[meter.plant_id] = meter_counts.get(meter.plant_id, 0) + 1
        non_primary = {
            plant_id
            for plant_id, count in meter_counts.items()
            if count != 1
            or not any(
                meter.is_primary
                for meter in revenue_meters
                if meter.plant_id == plant_id
            )
        }
        if non_primary:
            raise DataGenerationError(
                "Plants without exactly one primary revenue meter: "
                + ", ".join(sorted(non_primary))
            )

    def _validate_referential_integrity(
        self,
        plants: tuple[Plant, ...],
        equipment: tuple[Equipment, ...],
        revenue_meters: tuple[RevenueMeter, ...],
        weather: tuple[WeatherObservation, ...],
        inverter_scada: tuple[SCADAObservation, ...],
        plant_scada: tuple[PlantSCADAObservation, ...],
        ground_truth_events: pd.DataFrame,
        alarms: pd.DataFrame,
        incidents: pd.DataFrame,
        work_orders: pd.DataFrame,
    ) -> None:
        plant_ids = {plant.plant_id for plant in plants}
        equipment_ids = {item.equipment_id for item in equipment}
        meter_ids = {meter.meter_id for meter in revenue_meters}

        unknown_weather_plants = {item.plant_id for item in weather} - plant_ids
        if unknown_weather_plants:
            raise DataGenerationError(
                "Weather references unknown plant IDs: "
                + ", ".join(sorted(unknown_weather_plants))
            )

        unknown_scada_plants = {item.plant_id for item in inverter_scada} - plant_ids
        if unknown_scada_plants:
            raise DataGenerationError(
                "Inverter SCADA references unknown plant IDs: "
                + ", ".join(sorted(unknown_scada_plants))
            )

        unknown_scada_equipment = {
            item.equipment_id for item in inverter_scada
        } - equipment_ids
        if unknown_scada_equipment:
            raise DataGenerationError(
                "Inverter SCADA references unknown equipment IDs: "
                + ", ".join(sorted(unknown_scada_equipment))
            )

        unknown_plant_scada_plants = {item.plant_id for item in plant_scada} - plant_ids
        if unknown_plant_scada_plants:
            raise DataGenerationError(
                "Plant SCADA references unknown plant IDs: "
                + ", ".join(sorted(unknown_plant_scada_plants))
            )

        unknown_plant_scada_meters = {item.meter_id for item in plant_scada} - meter_ids
        if unknown_plant_scada_meters:
            raise DataGenerationError(
                "Plant SCADA references unknown meter IDs: "
                + ", ".join(sorted(unknown_plant_scada_meters))
            )

        if not ground_truth_events.empty:
            event_plant_ids = set(
                ground_truth_events["plant_id"].astype(str).str.upper()
            )
            unknown_event_plants = event_plant_ids - plant_ids
            if unknown_event_plants:
                raise DataGenerationError(
                    "Ground-truth events reference unknown plant IDs: "
                    + ", ".join(sorted(unknown_event_plants))
                )

        if not alarms.empty:
            alarm_plant_ids = set(alarms["plant_id"].astype(str).str.upper())
            unknown_alarm_plants = alarm_plant_ids - plant_ids
            if unknown_alarm_plants:
                raise DataGenerationError(
                    "Alarms reference unknown plant IDs: "
                    + ", ".join(sorted(unknown_alarm_plants))
                )

        if not incidents.empty:
            incident_plant_ids = set(incidents["plant_id"].astype(str).str.upper())
            unknown_incident_plants = incident_plant_ids - plant_ids
            if unknown_incident_plants:
                raise DataGenerationError(
                    "Incidents reference unknown plant IDs: "
                    + ", ".join(sorted(unknown_incident_plants))
                )

        if not work_orders.empty:
            work_order_plant_ids = set(work_orders["plant_id"].astype(str).str.upper())
            unknown_work_order_plants = work_order_plant_ids - plant_ids
            if unknown_work_order_plants:
                raise DataGenerationError(
                    "Work orders reference unknown plant IDs: "
                    + ", ".join(sorted(unknown_work_order_plants))
                )


def generate_dataset(
    config: GenerationConfig,
    random_context: RandomContext | None = None,
) -> SyntheticDataset:
    """Generate a complete in-memory synthetic master dataset."""
    generator = SyntheticDatasetGenerator(config, random_context)
    return generator.generate()


def _build_run_id(config: GenerationConfig) -> str:
    timestamp = config.time.start.strftime("%Y%m%dT%H%M%SZ")
    return f"{_DEFAULT_RUN_PREFIX}-{timestamp}-{config.seed}"


__all__ = [
    "GenerationSummary",
    "SyntheticDataset",
    "SyntheticDatasetGenerator",
    "generate_dataset",
]
