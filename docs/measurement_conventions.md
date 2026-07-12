# Measurement Conventions

**Project:** Energy Operations Intelligence Platform
**Document:** Measurement Conventions
**Version:** 1.0
**Status:** Approved for Development

---

## 1. Purpose

This document defines the canonical measurement units, timestamp semantics, equipment states, valid operating ranges, meter-reset rules, and loss categories used throughout the Energy Operations Intelligence Platform.

The objective is to ensure that data generation, ETL, SQL analytics, machine-learning features, and dashboard calculations use consistent engineering definitions.

The machine-readable source of truth is:

```text
configs/units.yaml

# Measurement Conventions

**Project:** Energy Operations Intelligence Platform
**Document:** Measurement Conventions
**Version:** 1.0
**Status:** Approved for Development

---

# 1. Purpose

This document establishes the official engineering measurement standards used throughout the Energy Operations Intelligence Platform.

Its objective is to ensure that every dataset, ETL pipeline, SQL query, machine learning model, dashboard visualization, and KPI calculation follows consistent engineering definitions and measurement semantics.

These conventions eliminate ambiguity, prevent inconsistent calculations, and provide a single source of truth for all analytical processes.

The machine-readable implementation of these standards is maintained in:

```
configs/units.yaml
```

---

# 2. Canonical Units

All incoming telemetry, maintenance, financial, and operational datasets must be converted into these canonical units before entering the curated analytical layer.

| Measurement | Canonical Unit | Symbol | Meaning |
|-------------|---------------|--------|---------|
| Active Power | kilowatt | kW | Instantaneous real power |
| Active Power | megawatt | MW | Large-scale instantaneous power |
| Energy | kilowatt-hour | kWh | Electrical energy accumulated over time |
| Energy | megawatt-hour | MWh | Large-scale electrical energy |
| Voltage | volt | V | Electrical potential difference |
| Current | ampere | A | Electrical current |
| Frequency | hertz | Hz | Electrical system frequency |
| Reactive Power | kilovar | kvar | Reactive electrical power |
| Apparent Power | kilovolt-ampere | kVA | Apparent electrical power |
| Irradiance | watt per square metre | W/m² | Solar irradiance incident on PV modules |
| Temperature | degree Celsius | °C | Ambient, module or equipment temperature |
| Duration | minute | min | Time duration |
| Duration | hour | h | Time duration |
| Currency | United States Dollar | USD | Financial values |

### Engineering Rule

All source measurements shall be converted into canonical units before they are published into analytical tables.

Raw source values may be preserved only inside the staging layer.

---

# 3. Power and Energy Semantics

One of the most common analytical mistakes in energy analytics is confusing power with energy.

The platform explicitly distinguishes these concepts.

---

## 3.1 Instantaneous Power

Power represents the rate at which electricity is generated, consumed, imported, or exported at a specific moment.

Canonical Units

- kW
- MW

Examples

- Inverter AC Output
- Plant Export Power
- Grid Import Power
- Feeder Load
- Transformer Output

Power must **never** be summed across time.

---

## 3.2 Interval Energy

Energy represents the quantity of electricity produced or consumed during a defined time interval.

Canonical Units

- kWh
- MWh

Energy is derived using:

```
Interval Energy (kWh)
=
Average Power (kW)
×
Interval Duration (hours)
```

For the platform's SCADA interval:

```
15 minutes
=
0.25 hours
```

Example

```
Average Power = 400 kW

Interval Energy

= 400 × 0.25

=100 kWh
```

---

## 3.3 Invalid Calculation

The following calculation is prohibited.

```
Sum(kW)

=

kWh
```

Power values must always be integrated over time before becoming energy.

---

# 4. DC Capacity and AC Capacity

The platform treats DC and AC capacities as different engineering quantities.

---

## 4.1 DC Capacity

DC Capacity represents installed photovoltaic module capacity under Standard Test Conditions (STC).

Canonical Unit

```
MWp
```

The suffix **p** denotes Peak Capacity.

Examples

- 25 MWp Solar Farm
- 350 MWp Portfolio

---

## 4.2 AC Capacity

AC Capacity represents inverter-limited or grid-export capacity.

Canonical Unit

```
MW
```

Examples

- 20 MW Inverter Capacity
- 18 MW Export Capacity

---

## 4.3 DC / AC Ratio

Formula

```
DC / AC Ratio

=

Installed DC Capacity (MWp)

/

Installed AC Capacity (MW)
```

Example

```
25 MWp

/

20 MW

=

1.25
```

DC Capacity and AC Capacity must never be used interchangeably.

---

# 5. Timestamp Convention

---

## 5.1 Time Zone

The platform stores all operational timestamps in

```
UTC
```

Local time is generated only for reporting and dashboard display.

---

## 5.2 Interval Convention

The platform follows the

```
Interval-End Convention
```

A timestamp identifies the **end** of the measurement interval.

Example

```
Timestamp

2025-01-01 00:15 UTC
```

represents

```
00:00

↓

00:15
```

not

```
00:15

↓

00:30
```

---

## 5.3 Standard SCADA Interval

Primary telemetry interval

```
15 minutes
```

Equivalent duration

```
0.25 Hours
```

---

## 5.4 Aggregation Rules

Energy

✓ Sum across intervals

Power

✓ Average

or

✓ Maximum

depending on the business calculation.

---

# 6. Cumulative Meter Handling

Many energy meters store cumulative readings rather than interval energy.

The platform standardizes how these are interpreted.

---

## 6.1 Expected Behaviour

Cumulative meters should always increase.

```
Current Reading

>=

Previous Reading
```

---

## 6.2 Interval Energy

```
Interval Energy

=

Current Reading

-

Previous Reading
```

---

## 6.3 Meter Reset Detection

A reset is detected when

```
Current Reading

-

Previous Reading

<

-Reset Tolerance
```

Default tolerance

```
1.0 kWh
```

---

## 6.4 Reset Handling

When a reset occurs the platform shall

- Preserve the original reading
- Flag the reset event
- Prevent negative interval energy
- Calculate interval energy using reset-aware logic
- Log the event in the audit table
- Maintain full traceability

---

## 6.5 Invalid Behaviour

The following action is prohibited

```
Negative Interval Energy

↓

Automatically Replace With Zero
```

without recording an audit event.

---

# 7. Valid Measurement Ranges

These represent default engineering validation limits.

Individual equipment may define narrower operating ranges.

| Measurement | Minimum | Maximum | Validation Note |
|-------------|---------|----------|----------------|
| AC Power | 0 kW | 110% Rated Power | Above requires validation |
| DC Power | 0 kW | 125% Rated Power | Allows DC oversizing |
| AC Voltage | 0 V | 1500 V | Equipment dependent |
| DC Voltage | 0 V | 2000 V | Equipment dependent |
| Current | 0 A | 5000 A | Depends on equipment |
| Frequency | 45 Hz | 55 Hz | Outside indicates abnormal operation |
| Power Factor | -1 | 1 | Signed value permitted |
| Reactive Power | -10000 kvar | 10000 kvar | Import/Export convention |
| Irradiance | 0 W/m² | 1400 W/m² | Above requires validation |
| Ambient Temperature | -20 °C | 60 °C | Default portfolio limit |
| Module Temperature | -20 °C | 90 °C | Default portfolio limit |
| Communication Quality | 0% | 100% | Percentage |

Measurements outside these limits must be

- rejected
- quarantined
- flagged

depending on configured validation rules.

---

# 8. Standardized Equipment States

Every asset shall be assigned exactly one canonical operating state.

| State | Definition |
|---------|------------|
| AVAILABLE | Ready for operation |
| RUNNING | Generating normally |
| STANDBY | Healthy but idle |
| DERATED | Operating below available capacity |
| CURTAILED | Output intentionally restricted |
| PLANNED_OUTAGE | Scheduled outage |
| FORCED_OUTAGE | Unplanned failure |
| GRID_UNAVAILABLE | Grid unavailable |
| COMMUNICATION_LOSS | Telemetry unavailable |
| MAINTENANCE | Under maintenance |
| UNKNOWN | State cannot be determined |

---

## 8.1 State Priority

If multiple conditions occur simultaneously, the following precedence applies

```
COMMUNICATION_LOSS

↓

FORCED_OUTAGE

↓

PLANNED_OUTAGE

↓

MAINTENANCE

↓

GRID_UNAVAILABLE

↓

CURTAILED

↓

DERATED

↓

RUNNING

↓

STANDBY

↓

AVAILABLE

↓

UNKNOWN
```

---

# 9. Standard Loss Categories

Every recoverable energy loss must belong to one standardized category.

| Category | Definition |
|----------|------------|
| GRID_OUTAGE | Grid unavailable |
| INVERTER_OUTAGE | Inverter failure |
| TRANSFORMER_OUTAGE | Transformer failure |
| CURTAILMENT | Export restriction |
| SOILING | Dirt accumulation |
| THERMAL_DERATING | High-temperature reduction |
| CLIPPING | Inverter clipping |
| COMMUNICATION_UNCERTAINTY | Missing telemetry |
| SENSOR_UNCERTAINTY | Sensor quality issue |
| PLANNED_MAINTENANCE | Scheduled maintenance |
| UNEXPLAINED_UNDERPERFORMANCE | Unknown performance loss |

---

## 9.1 Recoverability Classification

Each loss may later be classified as

- Avoidable
- Partially Avoidable
- External

Examples

| Category | Classification |
|-----------|----------------|
| Inverter Outage | Avoidable |
| Excessive Soiling | Avoidable |
| Long MTTR | Avoidable |
| Grid Outage | External |
| Curtailment | External / Contractual |
| Planned Maintenance | Necessary |
| Sensor Failure | Data Quality |

Financial recommendations must clearly distinguish recoverable losses from unavoidable losses.

---

# 10. Currency Convention

Canonical Currency

```
USD
```

Every financial calculation must include

- Currency
- Tariff Basis
- Effective Date
- Assumptions

Currency conversion is outside the scope of this project.

---

# 11. Data Governance Rules

The following governance rules apply throughout the platform.

1. Canonical units must be used in all curated datasets.
2. Raw units shall be preserved only within the staging layer.
3. Unit conversions must be deterministic.
4. Conversion logic must never be duplicated.
5. KPI calculations shall reference standardized measurements.
6. Every dashboard visualization shall display engineering units.
7. Derived metrics must document their source measurements.
8. Measurement-rule changes require version control.
9. All transformations must remain traceable to raw telemetry.
10. Invalid measurements must never be silently discarded.

---

# 12. Machine-Readable Configuration

The engineering source of truth is

```
configs/units.yaml
```

Application code should load

- conversion factors
- valid ranges
- equipment states
- measurement semantics
- loss categories

directly from this configuration file.

---

# 13. Change Control

Any modification to measurement conventions requires

1. Update `configs/units.yaml`
2. Update `measurement_conventions.md`
3. Update unit tests
4. Review ETL transformations
5. Review KPI calculations
6. Version-controlled Git commit
7. Engineering approval before deployment

---

# Document Approval

| Item | Value |
|------|-------|
| Owner | Energy Analytics Team |
| Approved By | Project Lead |
| Version | 1.0 |
| Status | Approved for Development |
| Last Updated | Phase 2 |

---

**End of Document**
