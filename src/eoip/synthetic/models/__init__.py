"""
Public exports for EOIP synthetic domain models.

This module exposes the stable public API for all synthetic domain models.
Applications should import models from this package rather than individual
modules whenever possible.
"""

from eoip.synthetic.models.alarm import Alarm, AlarmSeverity, AlarmStatus
from eoip.synthetic.models.budget import Budget
from eoip.synthetic.models.equipment import (
    Equipment,
    EquipmentStatus,
    EquipmentType,
)
from eoip.synthetic.models.ground_truth import (
    GroundTruthEvent,
    GroundTruthEventType,
)
from eoip.synthetic.models.incident import (
    Incident,
    IncidentStatus,
)
from eoip.synthetic.models.meter import (
    MeterAccuracyClass,
    MeterStatus,
    RevenueMeter,
)
from eoip.synthetic.models.plant import Plant, PlantStatus
from eoip.synthetic.models.plant_scada import (
    PlantSCADAObservation,
    PlantSCADAQuality,
)
from eoip.synthetic.models.scada import SCADAObservation
from eoip.synthetic.models.tariff import Tariff
from eoip.synthetic.models.weather import (
    WeatherObservation,
    WeatherQuality,
)
from eoip.synthetic.models.work_order import (
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
)

__all__ = [
    # Plant
    "Plant",
    "PlantStatus",
    # Equipment
    "Equipment",
    "EquipmentType",
    "EquipmentStatus",
    # Revenue Meter
    "RevenueMeter",
    "MeterAccuracyClass",
    "MeterStatus",
    # Weather
    "WeatherObservation",
    "WeatherQuality",
    # SCADA
    "SCADAObservation",
    "PlantSCADAObservation",
    "PlantSCADAQuality",
    # Alarm
    "Alarm",
    "AlarmSeverity",
    "AlarmStatus",
    # Incident
    "Incident",
    "IncidentStatus",
    # Work Order
    "WorkOrder",
    "WorkOrderPriority",
    "WorkOrderStatus",
    # Tariff
    "Tariff",
    # Budget
    "Budget",
    # Ground Truth
    "GroundTruthEvent",
    "GroundTruthEventType",
]
