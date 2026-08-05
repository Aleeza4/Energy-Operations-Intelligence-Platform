"""Synthetic data generators for EOIP master-data domains."""

from eoip.synthetic.generators.equipment_generator import (
    EquipmentGeneratorConfig,
    generate_equipment,
    generate_equipment_records,
)
from eoip.synthetic.generators.plant_generator import (
    PlantGeneratorConfig,
    generate_plant_records,
    generate_plants,
)
from eoip.synthetic.generators.scada_generator import (
    SCADAGeneratorConfig,
    generate_scada,
    generate_scada_records,
)

__all__ = [
    "EquipmentGeneratorConfig",
    "PlantGeneratorConfig",
    "SCADAGeneratorConfig",
    "generate_equipment",
    "generate_equipment_records",
    "generate_plant_records",
    "generate_plants",
    "generate_scada",
    "generate_scada_records",
]
