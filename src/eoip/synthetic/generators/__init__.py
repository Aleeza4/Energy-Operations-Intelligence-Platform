"""Synthetic data generators for EOIP master-data domains."""

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
    generate_equipment,
    generate_equipment_records,
)
from eoip.synthetic.generators.meter_generator import (
    MeterGeneratorConfig,
    generate_revenue_meter_records,
    generate_revenue_meters,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
    generate_plant_records,
    generate_plants,
)
from eoip.synthetic.generators.plant_scada_generator import (
    PlantSCADAGeneratorConfig,
    generate_plant_scada,
    generate_plant_scada_records,
)
from eoip.synthetic.generators.scada_generator import (
    SCADAGeneratorConfig,
    generate_scada,
    generate_scada_records,
)

__all__ = [
    "EquipmentGeneratorConfig",
    "MeterGeneratorConfig",
    "PlantGeneratorConfig",
    "PlantSCADAGeneratorConfig",
    "SCADAGeneratorConfig",
    "generate_equipment",
    "generate_equipment_records",
    "generate_revenue_meter_records",
    "generate_revenue_meters",
    "generate_plant_records",
    "generate_plants",
    "generate_plant_scada",
    "generate_plant_scada_records",
    "generate_scada",
    "generate_scada_records",
]
