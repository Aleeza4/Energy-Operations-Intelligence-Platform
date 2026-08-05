# EOIP Requirements Traceability Matrix (RTM)

> Purpose:
> Track every major project requirement from planning through implementation and testing.
>
> Rule:
> Every implemented feature must be linked to at least one production file and one test file.

---

# Status Legend

| Status | Meaning |
|---------|---------|
| ⏳ | Not Started |
| 🚧 | In Progress |
| ✅ | Completed |

---

# Phase 2 – Synthetic Data Engine

| Requirement | Production File(s) | Test File(s) | Status |
|--------------|--------------------|--------------|--------|
| Plant Model | plant.py | test_plant.py | ✅ |
| Equipment Model | equipment.py | test_equipment.py | ✅ |
| Weather Model | weather.py | test_weather.py | ✅ |
| Alarm Model | alarm.py | test_alarm.py | ✅ |
| Incident Model | incident.py | test_incident.py | ⏳ |
| Work Order Model | work_order.py | test_work_order.py | ⏳ |
| Plant Generator | plant_generator.py | test_plant_generator.py | ✅ |
| Equipment Generator | equipment_generator.py | test_equipment_generator.py | ✅ |
| Weather Generator | weather_generator.py | test_weather_generator.py | ✅ |
| SCADA Generator | scada_generator.py | test_scada_generator.py | ⏳ |
| Meter Generator | meter_generator.py | test_meter_generator.py | ⏳ |
| Event Catalogue | catalogue.py | test_catalogue.py | ✅ |
| Event Scheduler | scheduler.py | test_scheduler.py | ✅ |
| Event Effects | effects.py | test_effects.py | 🚧 |
| Alarm Engine | alarms.py | test_alarms.py | ⏳ |
| Incident Engine | incidents.py | test_incidents.py | ⏳ |
| Work Order Engine | work_orders.py | test_work_orders.py | ⏳ |
| Synthetic Pipeline | pipeline.py | test_pipeline.py | ⏳ |

---

# Update Rules

1. Every new requirement must be added here.
2. Every production file must have a corresponding test file.
3. A requirement is marked **Completed** only after:
   - Production code is complete.
   - Tests pass.
   - Ruff passes.
   - Black passes.
4. Before starting a new feature, verify it exists in this matrix.