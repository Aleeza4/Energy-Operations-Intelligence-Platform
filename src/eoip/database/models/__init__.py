"""
EOIP SQLAlchemy ORM models.
"""

from eoip.database.models.alarm import AlarmORM
from eoip.database.models.budget import BudgetORM
from eoip.database.models.equipment import EquipmentORM
from eoip.database.models.ground_truth import GroundTruthEventORM
from eoip.database.models.incident import IncidentORM
from eoip.database.models.plant import PlantORM
from eoip.database.models.scada import SCADAObservationORM
from eoip.database.models.tariff import TariffORM
from eoip.database.models.weather import WeatherObservationORM
from eoip.database.models.work_order import WorkOrderORM

__all__ = [
    "AlarmORM",
    "BudgetORM",
    "EquipmentORM",
    "GroundTruthEventORM",
    "IncidentORM",
    "PlantORM",
    "SCADAObservationORM",
    "TariffORM",
    "WeatherObservationORM",
    "WorkOrderORM",
]
