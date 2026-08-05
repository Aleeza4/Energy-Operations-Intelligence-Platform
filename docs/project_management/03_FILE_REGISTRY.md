# EOIP File Registry

> **Purpose**
>
> This document is the master inventory of every file in the project.
> Before creating, modifying, or deleting any file, check this registry first.
>
> **Rule:** No file should exist without being registered here.

---

# Status Legend

| Status | Meaning |
|----------|---------|
| ⏳ | Not Started |
| 🚧 | In Progress |
| ✅ | Completed |
| 🧪 | Testing |
| 🔄 | Refactoring |
| ❌ | Deprecated |

---

# Phase 2 – Physics-Informed Synthetic Data Engine

## Models

| File | Status | Test File | Ruff | Black | Pytest | Notes |
|------|--------|-----------|-------|--------|---------|------|
| plant.py | ✅ | test_plant.py | ✅ | ✅ | ✅ | Completed |
| equipment.py | ✅ | test_equipment.py | ✅ | ✅ | ✅ | Completed |
| weather.py | ✅ | test_weather.py | ✅ | ✅ | ✅ | Completed |
| alarm.py | ✅ | test_alarm.py | ✅ | ✅ | ✅ | Completed |
| incident.py | ⏳ | test_incident.py | ⏳ | ⏳ | ⏳ | Not Started |
| work_order.py | ⏳ | test_work_order.py | ⏳ | ⏳ | ⏳ | Not Started |

---

## Generators

| File | Status | Test File | Ruff | Black | Pytest | Notes |
|------|--------|-----------|-------|--------|---------|------|
| plant_generator.py | ✅ | test_plant_generator.py | ✅ | ✅ | ✅ | Completed |
| equipment_generator.py | ✅ | test_equipment_generator.py | ✅ | ✅ | ✅ | Completed |
| weather_generator.py | ✅ | test_weather_generator.py | ✅ | ✅ | ✅ | Completed |
| scada_generator.py | ⏳ | test_scada_generator.py | ⏳ | ⏳ | ⏳ | Not Started |
| meter_generator.py | ⏳ | test_meter_generator.py | ⏳ | ⏳ | ⏳ | Not Started |

---

## Events

| File | Status | Test File | Ruff | Black | Pytest | Notes |
|------|--------|-----------|-------|--------|---------|------|
| catalogue.py | ✅ | test_catalogue.py | ✅ | ✅ | ✅ | Completed |
| scheduler.py | ✅ | test_scheduler.py | ✅ | ✅ | ✅ | Completed |
| effects.py | ✅ | test_effects.py | 🚧 | 🚧 | 🚧 | Test pending |

---

## Operations

| File | Status | Test File | Ruff | Black | Pytest | Notes |
|------|--------|-----------|-------|--------|---------|------|
| alarms.py | ⏳ | test_alarms.py | ⏳ | ⏳ | ⏳ | Not Started |
| incidents.py | ⏳ | test_incidents.py | ⏳ | ⏳ | ⏳ | Not Started |
| work_orders.py | ⏳ | test_work_orders.py | ⏳ | ⏳ | ⏳ | Not Started |

---

## Pipeline

| File | Status | Test File | Ruff | Black | Pytest | Notes |
|------|--------|-----------|-------|--------|---------|------|
| pipeline.py | ⏳ | test_pipeline.py | ⏳ | ⏳ | ⏳ | Not Started |

---

# Rules

1. Every production file must have a corresponding test file.
2. Do not create duplicate files.
3. Update the status immediately after completing work.
4. Mark a file as **Completed** only after Ruff, Black, and Pytest all pass.
5. Before starting any new work, check this registry first.