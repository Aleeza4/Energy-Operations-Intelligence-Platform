# EOIP Dependency Map

> This document shows how the major modules depend on each other.
> Always review this before making architectural changes.

---

# High-Level Flow

Phase 0
↓
Phase 1
↓
Phase 2
↓
Phase 3
↓
Phase 4
↓
Phase 5
↓
Phase 6
↓
Phase 7
↓
Phase 8
↓
Phase 9
↓
Phase 10
↓
Phase 11
↓
Phase 12
↓
Phase 13
↓
Phase 14
↓
Phase 15

---

# Phase 2 Module Dependencies

Models
│
├── Plant
├── Equipment
├── Weather
├── Alarm
├── Incident
└── Work Order
        │
        ▼
Generators
│
├── Plant Generator
├── Equipment Generator
├── Weather Generator
├── SCADA Generator
└── Meter Generator
        │
        ▼
Event Engine
│
├── Event Catalogue
├── Event Scheduler
└── Event Effects
        │
        ▼
Operations Engine
│
├── Alarm Engine
├── Incident Engine
└── Work Order Engine
        │
        ▼
Pipeline
│
└── pipeline.py

---

# Dependency Rules

1. Models do not depend on Generators.
2. Generators depend only on Models.
3. Event Engine depends on Models and Generators.
4. Operations Engine depends on Events.
5. Pipeline depends on all completed modules.
6. Avoid circular dependencies.
7. Update this document whenever a new major dependency is introduced.