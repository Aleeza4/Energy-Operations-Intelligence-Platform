# KPI Dictionary

**Project:** Energy Operations Intelligence Platform (EOIP)
**Document:** KPI Dictionary
**Version:** 1.0
**Status:** Draft
**Prepared By:** Energy Analytics Consultant

---

# Purpose

This document defines the business, operational, engineering, financial, and data quality Key Performance Indicators (KPIs) used throughout the Energy Operations Intelligence Platform.

Each KPI has a standardized definition, calculation methodology, target threshold, reporting frequency, and business owner to ensure consistency across analytics, dashboards, executive reporting, and machine learning models.

---

# KPI Classification

The KPIs are grouped into five categories:

1. Solar Performance KPIs
2. Reliability & Operations KPIs
3. Load & Demand KPIs
4. Financial KPIs
5. Data Quality KPIs

---

# Solar Performance KPIs

---

## KPI 1 — Actual Energy Generation

| Field | Value |
|------|------|
| **KPI Name** | Actual Energy Generation |
| **Abbreviation** | AEG |
| **Definition** | Total electrical energy exported by the plant during the reporting period. Represents the actual measured energy delivered to the grid. |
| **Formula** | Sum(Energy Exported) |
| **Unit** | MWh |
| **Calculation Frequency** | Every 15 minutes, Hourly, Daily, Monthly |
| **Target** | As close as possible to Expected Energy |
| **Data Source** | Revenue Meter, SCADA |
| **Primary Users** | Executive, Operations Manager, Plant Engineer |

---

## KPI 2 — Expected Energy Generation

| Field | Value |
|------|------|
| **KPI Name** | Expected Energy Generation |
| **Abbreviation** | EEG |
| **Definition** | Theoretical energy generation under current irradiance and environmental conditions after applying engineering assumptions and equipment characteristics. |
| **Formula** | Irradiance × Installed Capacity × Performance Model |
| **Unit** | MWh |
| **Calculation Frequency** | Every 15 minutes |
| **Target** | Reference Value |
| **Data Source** | Weather Model, SCADA, Plant Configuration |
| **Primary Users** | Executive, Engineer |

---

## KPI 3 — Energy Yield

| Field | Value |
|------|------|
| **KPI Name** | Energy Yield |
| **Abbreviation** | EY |
| **Definition** | Total energy generated during a reporting period regardless of plant size. |
| **Formula** | Total Energy Generated |
| **Unit** | MWh |
| **Calculation Frequency** | Daily, Monthly |
| **Target** | Site-specific |
| **Data Source** | SCADA |
| **Primary Users** | Executive, Engineer |

---

## KPI 4 — Specific Yield

| Field | Value |
|------|------|
| **KPI Name** | Specific Yield |
| **Abbreviation** | SY |
| **Definition** | Energy generated per MWp of installed DC capacity. Used for comparing plants of different sizes. |
| **Formula** | Total Energy Generated ÷ Installed Capacity |
| **Unit** | kWh/kWp |
| **Calculation Frequency** | Daily, Monthly |
| **Target** | Depends on geography |
| **Data Source** | SCADA + Plant Master Data |
| **Primary Users** | Executive, Engineer |

---

## KPI 5 — Performance Ratio

| Field | Value |
|------|------|
| **KPI Name** | Performance Ratio |
| **Abbreviation** | PR |
| **Definition** | Indicates how efficiently a solar plant converts available solar energy into electrical energy after accounting for all losses. |
| **Formula** | Actual Energy ÷ Expected Energy × 100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | >80% (Typical Utility Scale) |
| **Data Source** | SCADA + Weather |
| **Primary Users** | Executive, Engineer |

---

## KPI 6 — Performance Ratio Gap

| Field | Value |
|------|------|
| **KPI Name** | Performance Ratio Gap |
| **Abbreviation** | PR Gap |
| **Definition** | Difference between target performance ratio and actual performance ratio. Highlights underperforming plants. |
| **Formula** | Target PR − Actual PR |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | <2% |
| **Data Source** | KPI Engine |
| **Primary Users** | Executive, Engineer |

---

## KPI 7 — Capacity Factor

| Field | Value |
|------|------|
| **KPI Name** | Capacity Factor |
| **Abbreviation** | CF |
| **Definition** | Measures actual energy production relative to the maximum theoretical production if the plant operated at full capacity continuously. |
| **Formula** | Actual Energy ÷ (Installed Capacity × Time) |
| **Unit** | % |
| **Calculation Frequency** | Monthly |
| **Target** | Plant-specific |
| **Data Source** | SCADA |
| **Primary Users** | Executive |

---

## KPI 8 — Inverter Efficiency

| Field | Value |
|------|------|
| **KPI Name** | Inverter Efficiency |
| **Abbreviation** | INV Eff |
| **Definition** | Percentage of DC power successfully converted into AC power by the inverter. |
| **Formula** | AC Power ÷ DC Power ×100 |
| **Unit** | % |
| **Calculation Frequency** | Every 15 Minutes |
| **Target** | >97% |
| **Data Source** | Inverter Telemetry |
| **Primary Users** | Engineer |

---

## KPI 9 — DC/AC Ratio

| Field | Value |
|------|------|
| **KPI Name** | DC/AC Ratio |
| **Abbreviation** | DCAC |
| **Definition** | Ratio between installed DC capacity and AC export capacity. Used to evaluate clipping risk. |
| **Formula** | Installed DC Capacity ÷ Installed AC Capacity |
| **Unit** | Ratio |
| **Calculation Frequency** | Static |
| **Target** | 1.1–1.4 |
| **Data Source** | Plant Configuration |
| **Primary Users** | Engineer |

---

## KPI 10 — Soiling Loss Estimate

| Field | Value |
|------|------|
| **KPI Name** | Soiling Loss Estimate |
| **Abbreviation** | SLE |
| **Definition** | Estimated energy loss caused by dirt accumulation on PV modules. |
| **Formula** | Expected Energy − Corrected Clean Energy Estimate |
| **Unit** | % |
| **Calculation Frequency** | Weekly |
| **Target** | <3% |
| **Data Source** | Weather + SCADA |
| **Primary Users** | Engineer |

---

## KPI 11 — Curtailment Loss

| Field | Value |
|------|------|
| **KPI Name** | Curtailment Loss |
| **Abbreviation** | CL |
| **Definition** | Energy not exported due to grid operator restrictions despite available generation capacity. |
| **Formula** | Potential Generation − Exported Energy |
| **Unit** | MWh |
| **Calculation Frequency** | Daily |
| **Target** | Minimize |
| **Data Source** | Grid Events |
| **Primary Users** | Executive, Operations |

---

## KPI 12 — Clipping Loss

| Field | Value |
|------|------|
| **KPI Name** | Clipping Loss |
| **Abbreviation** | CPL |
| **Definition** | Energy lost because inverter AC capacity limits output while DC generation exceeds inverter rating. |
| **Formula** | Potential DC Output − AC Output |
| **Unit** | MWh |
| **Calculation Frequency** | Daily |
| **Target** | Engineering Dependent |
| **Data Source** | Inverter Telemetry |
| **Primary Users** | Engineer |

---

## KPI 13 — Thermal Derating Loss

| Field | Value |
|------|------|
| **KPI Name** | Thermal Derating Loss |
| **Abbreviation** | TDL |
| **Definition** | Estimated production loss caused by elevated module or inverter temperatures reducing efficiency. |
| **Formula** | Expected Energy − Temperature Corrected Energy |
| **Unit** | MWh |
| **Calculation Frequency** | Daily |
| **Target** | Minimize |
| **Data Source** | Weather Station + SCADA |
| **Primary Users** | Engineer |

---

## KPI 14 — Availability Loss

| Field | Value |
|------|------|
| **KPI Name** | Availability Loss |
| **Abbreviation** | AL |
| **Definition** | Estimated energy loss caused by equipment outages and unavailable assets. |
| **Formula** | Expected Energy During Downtime |
| **Unit** | MWh |
| **Calculation Frequency** | Daily |
| **Target** | <1% |
| **Data Source** | Incident Database |
| **Primary Users** | Executive, Engineer |

---

## KPI 15 — Recoverable Energy Opportunity

| Field | Value |
|------|------|
| **KPI Name** | Recoverable Energy Opportunity |
| **Abbreviation** | REO |
| **Definition** | Estimated amount of energy that could be recovered through operational improvements. |
| **Formula** | Sum(Avoidable Losses) |
| **Unit** | MWh |
| **Calculation Frequency** | Monthly |
| **Target** | Maximize Recovery |
| **Data Source** | Analytics Engine |
| **Primary Users** | Executive |

---

# End of Part 1

The next section of this document contains:

- Technical Availability
- Grid Availability
- Contractual Availability
- MTBF
- MTTR
- Mean Time to Acknowledge
- Mean Time to Respond
- SLA Compliance
- Repeat Fault Rate
- First Time Fix Rate
- Alarm Storm Frequency
- Energy Not Supplied
- Communication Availability
- and all remaining Reliability & Operations KPIs.

# Reliability & Operations KPIs

---

## KPI 16 — Technical Availability

| Field | Value |
|------|------|
| **KPI Name** | Technical Availability |
| **Abbreviation** | TA |
| **Definition** | Percentage of time the plant is technically capable of producing electricity, excluding approved external constraints such as grid outages. |
| **Formula** | (Available Time ÷ Total Time) × 100 |
| **Unit** | % |
| **Calculation Frequency** | Daily, Monthly |
| **Target** | ≥ 99.0% |
| **Data Source** | SCADA, Incident Management |
| **Primary Users** | Executive, Operations Manager, Plant Engineer |

---

## KPI 17 — Grid Availability

| Field | Value |
|------|------|
| **KPI Name** | Grid Availability |
| **Abbreviation** | GA |
| **Definition** | Percentage of time the electrical grid is available to receive generated power. |
| **Formula** | (Grid Available Time ÷ Total Time) × 100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | ≥ 99.5% |
| **Data Source** | Grid Event Logs |
| **Primary Users** | Executive, Operations Manager |

---

## KPI 18 — Contractual Availability

| Field | Value |
|------|------|
| **KPI Name** | Contractual Availability |
| **Abbreviation** | CA |
| **Definition** | Availability calculated according to contractual rules after excluding approved outages and force majeure events. |
| **Formula** | Contract Definition |
| **Unit** | % |
| **Calculation Frequency** | Monthly |
| **Target** | ≥ 98% |
| **Data Source** | Contract Rules + Incident Database |
| **Primary Users** | Executive |

---

## KPI 19 — Mean Time Between Failures

| Field | Value |
|------|------|
| **KPI Name** | Mean Time Between Failures |
| **Abbreviation** | MTBF |
| **Definition** | Average operating time between consecutive equipment failures. Indicates asset reliability. |
| **Formula** | Operating Hours ÷ Number of Failures |
| **Unit** | Hours |
| **Calculation Frequency** | Weekly, Monthly |
| **Target** | Increase over time |
| **Data Source** | Maintenance History |
| **Primary Users** | Engineer, Operations Manager |

---

## KPI 20 — Mean Time To Repair

| Field | Value |
|------|------|
| **KPI Name** | Mean Time To Repair |
| **Abbreviation** | MTTR |
| **Definition** | Average time required to restore equipment after a failure occurs. |
| **Formula** | Total Repair Time ÷ Number of Repairs |
| **Unit** | Hours |
| **Calculation Frequency** | Weekly |
| **Target** | <4 Hours (Example SLA) |
| **Data Source** | Work Orders |
| **Primary Users** | Engineer |

---

## KPI 21 — Mean Time To Acknowledge

| Field | Value |
|------|------|
| **KPI Name** | Mean Time To Acknowledge |
| **Abbreviation** | MTTA |
| **Definition** | Average time between alarm generation and acknowledgement by SOC operators. |
| **Formula** | Σ(Acknowledgement Time − Alarm Time) ÷ Total Alarms |
| **Unit** | Minutes |
| **Calculation Frequency** | Daily |
| **Target** | <5 Minutes |
| **Data Source** | RMS Alarm System |
| **Primary Users** | Operations Manager |

---

## KPI 22 — Mean Time To Respond

| Field | Value |
|------|------|
| **KPI Name** | Mean Time To Respond |
| **Abbreviation** | MTTRsp |
| **Definition** | Average time between alarm acknowledgement and first operational action. |
| **Formula** | Response Time ÷ Total Incidents |
| **Unit** | Minutes |
| **Calculation Frequency** | Daily |
| **Target** | <15 Minutes |
| **Data Source** | Incident Management |
| **Primary Users** | Operations Manager |

---

## KPI 23 — Mean Time To Restore Service

| Field | Value |
|------|------|
| **KPI Name** | Mean Time To Restore Service |
| **Abbreviation** | MTRS |
| **Definition** | Average time required to fully restore equipment or plant operation after an outage. |
| **Formula** | Total Restoration Time ÷ Number of Incidents |
| **Unit** | Hours |
| **Calculation Frequency** | Weekly |
| **Target** | Continuous Improvement |
| **Data Source** | Maintenance Records |
| **Primary Users** | Engineer |

---

## KPI 24 — SLA Compliance Rate

| Field | Value |
|------|------|
| **KPI Name** | SLA Compliance Rate |
| **Abbreviation** | SLA |
| **Definition** | Percentage of alarms or incidents handled within agreed response and resolution targets. |
| **Formula** | SLA Compliant Incidents ÷ Total Incidents ×100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | ≥95% |
| **Data Source** | Incident Database |
| **Primary Users** | Operations Manager |

---

## KPI 25 — Repeat Fault Rate

| Field | Value |
|------|------|
| **KPI Name** | Repeat Fault Rate |
| **Abbreviation** | RFR |
| **Definition** | Percentage of faults recurring within a defined period after maintenance. |
| **Formula** | Repeat Faults ÷ Total Faults ×100 |
| **Unit** | % |
| **Calculation Frequency** | Monthly |
| **Target** | <5% |
| **Data Source** | Fault History |
| **Primary Users** | Engineer |

---

## KPI 26 — First Time Fix Rate

| Field | Value |
|------|------|
| **KPI Name** | First Time Fix Rate |
| **Abbreviation** | FTFR |
| **Definition** | Percentage of maintenance work orders successfully resolved during the first visit. |
| **Formula** | Successful First Repairs ÷ Total Repairs ×100 |
| **Unit** | % |
| **Calculation Frequency** | Monthly |
| **Target** | ≥90% |
| **Data Source** | Work Orders |
| **Primary Users** | Engineer |

---

## KPI 27 — Alarm Storm Frequency

| Field | Value |
|------|------|
| **KPI Name** | Alarm Storm Frequency |
| **Abbreviation** | ASF |
| **Definition** | Number of alarm storms where alarm rates exceed predefined operational thresholds. |
| **Formula** | Count of Alarm Storm Events |
| **Unit** | Events |
| **Calculation Frequency** | Daily |
| **Target** | Zero |
| **Data Source** | RMS Alarm Logs |
| **Primary Users** | Operations Manager |

---

## KPI 28 — Critical Alarm Count

| Field | Value |
|------|------|
| **KPI Name** | Critical Alarm Count |
| **Abbreviation** | CAC |
| **Definition** | Total number of active alarms classified as Critical severity. |
| **Formula** | Count(Critical Alarms) |
| **Unit** | Count |
| **Calculation Frequency** | Real-Time |
| **Target** | As Low As Possible |
| **Data Source** | RMS |
| **Primary Users** | Operations Manager |

---

## KPI 29 — Incident Resolution Rate

| Field | Value |
|------|------|
| **KPI Name** | Incident Resolution Rate |
| **Abbreviation** | IRR |
| **Definition** | Percentage of incidents successfully resolved within the reporting period. |
| **Formula** | Closed Incidents ÷ Total Incidents ×100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | ≥95% |
| **Data Source** | Incident Management System |
| **Primary Users** | Operations Manager |

---

## KPI 30 — Downtime Duration

| Field | Value |
|------|------|
| **KPI Name** | Downtime Duration |
| **Abbreviation** | DT |
| **Definition** | Total duration equipment or plants remain unavailable due to faults or maintenance. |
| **Formula** | Σ Downtime Hours |
| **Unit** | Hours |
| **Calculation Frequency** | Daily |
| **Target** | Minimize |
| **Data Source** | SCADA + Incident Logs |
| **Primary Users** | Executive, Engineer |

---

## KPI 31 — Forced Outage Rate

| Field | Value |
|------|------|
| **KPI Name** | Forced Outage Rate |
| **Abbreviation** | FOR |
| **Definition** | Percentage of operating time lost due to unplanned outages. |
| **Formula** | Forced Outage Time ÷ Total Operating Time ×100 |
| **Unit** | % |
| **Calculation Frequency** | Monthly |
| **Target** | <1% |
| **Data Source** | Incident Management |
| **Primary Users** | Executive |

---

## KPI 32 — Planned Maintenance Compliance

| Field | Value |
|------|------|
| **KPI Name** | Planned Maintenance Compliance |
| **Abbreviation** | PMC |
| **Definition** | Percentage of scheduled maintenance completed within the planned maintenance window. |
| **Formula** | Completed Planned Work Orders ÷ Planned Work Orders ×100 |
| **Unit** | % |
| **Calculation Frequency** | Monthly |
| **Target** | ≥95% |
| **Data Source** | CMMS / Work Orders |
| **Primary Users** | Engineer |

---

## KPI 33 — Communication Availability

| Field | Value |
|------|------|
| **KPI Name** | Communication Availability |
| **Abbreviation** | Comm Avail |
| **Definition** | Percentage of time communication links between field devices and monitoring systems remain operational. |
| **Formula** | Communication Uptime ÷ Total Time ×100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | ≥99.8% |
| **Data Source** | RMS |
| **Primary Users** | Operations Manager, Platform Administrator |

---

## KPI 34 — Energy Not Supplied

| Field | Value |
|------|------|
| **KPI Name** | Energy Not Supplied |
| **Abbreviation** | ENS |
| **Definition** | Estimated electrical energy that could not be delivered due to outages or operational failures. |
| **Formula** | Expected Generation − Actual Generation During Outage |
| **Unit** | MWh |
| **Calculation Frequency** | Daily |
| **Target** | Minimize |
| **Data Source** | SCADA + Incident Database |
| **Primary Users** | Executive, Engineer |

---

## KPI 35 — Maintenance Backlog

| Field | Value |
|------|------|
| **KPI Name** | Maintenance Backlog |
| **Abbreviation** | MB |
| **Definition** | Number of outstanding maintenance work orders awaiting completion. |
| **Formula** | Count(Open Work Orders) |
| **Unit** | Count |
| **Calculation Frequency** | Daily |
| **Target** | Within Planning Capacity |
| **Data Source** | CMMS |
| **Primary Users** | Plant Engineer |

---

# End of Part 2

The next section continues with:

- Peak Demand
- Load Factor
- Power Factor
- Demand Ramp Rate
- Coincident Peak
- Demand Charge Exposure

followed by all Financial KPIs.

# Load & Demand KPIs

---

## KPI 36 — Peak Demand

| Field | Value |
|------|------|
| **KPI Name** | Peak Demand |
| **Abbreviation** | PD |
| **Definition** | Highest instantaneous electrical demand recorded during the reporting period. Peak demand directly influences demand charges and network loading. |
| **Formula** | MAX(Active Power) |
| **Unit** | MW |
| **Calculation Frequency** | Every 15 Minutes, Daily, Monthly |
| **Target** | Within Design Capacity |
| **Data Source** | Smart Meter, SCADA |
| **Primary Users** | Executive, Operations Manager |

---

## KPI 37 — Average Demand

| Field | Value |
|------|------|
| **KPI Name** | Average Demand |
| **Abbreviation** | AvgD |
| **Definition** | Average electrical demand during the reporting period. Used as the baseline for load profile analysis. |
| **Formula** | Total Energy ÷ Operating Hours |
| **Unit** | MW |
| **Calculation Frequency** | Daily |
| **Target** | Informational |
| **Data Source** | Smart Meter |
| **Primary Users** | Operations Manager |

---

## KPI 38 — Load Factor

| Field | Value |
|------|------|
| **KPI Name** | Load Factor |
| **Abbreviation** | LF |
| **Definition** | Measures how efficiently electrical demand is distributed over time by comparing average demand with peak demand. Higher values indicate a more stable demand profile. |
| **Formula** | Average Demand ÷ Peak Demand ×100 |
| **Unit** | % |
| **Calculation Frequency** | Monthly |
| **Target** | >70% |
| **Data Source** | Smart Meter |
| **Primary Users** | Executive |

---

## KPI 39 — Power Factor

| Field | Value |
|------|------|
| **KPI Name** | Power Factor |
| **Abbreviation** | PF |
| **Definition** | Ratio of active power to apparent power, indicating how effectively electrical power is converted into useful work. Poor power factor increases transmission losses and utility penalties. |
| **Formula** | Active Power ÷ Apparent Power |
| **Unit** | Ratio |
| **Calculation Frequency** | Every 15 Minutes |
| **Target** | ≥0.98 |
| **Data Source** | SCADA, Revenue Meter |
| **Primary Users** | Engineer |

---

## KPI 40 — Reactive Power

| Field | Value |
|------|------|
| **KPI Name** | Reactive Power |
| **Abbreviation** | Q |
| **Definition** | Electrical power required to maintain voltage stability within the power system. |
| **Formula** | Measured Reactive Power |
| **Unit** | MVAR |
| **Calculation Frequency** | Every 15 Minutes |
| **Target** | Within Grid Code |
| **Data Source** | SCADA |
| **Primary Users** | Engineer |

---

## KPI 41 — Demand Ramp Rate

| Field | Value |
|------|------|
| **KPI Name** | Demand Ramp Rate |
| **Abbreviation** | DRR |
| **Definition** | Measures the rate at which electrical demand changes between consecutive measurement intervals. Large ramp rates may indicate instability or rapid operational changes. |
| **Formula** | (Current Demand − Previous Demand) ÷ Time Interval |
| **Unit** | MW/min |
| **Calculation Frequency** | Every 15 Minutes |
| **Target** | Operationally Stable |
| **Data Source** | SCADA |
| **Primary Users** | Operations Manager |

---

## KPI 42 — Coincident Peak Demand

| Field | Value |
|------|------|
| **KPI Name** | Coincident Peak Demand |
| **Abbreviation** | CPD |
| **Definition** | Plant demand measured during the utility's system-wide peak demand period. Often used for transmission and demand charge calculations. |
| **Formula** | Demand at Utility Peak Interval |
| **Unit** | MW |
| **Calculation Frequency** | Monthly |
| **Target** | Minimize |
| **Data Source** | Utility Meter |
| **Primary Users** | Executive |

---

## KPI 43 — Demand Charge Exposure

| Field | Value |
|------|------|
| **KPI Name** | Demand Charge Exposure |
| **Abbreviation** | DCE |
| **Definition** | Estimated financial exposure caused by high peak demand under the applicable electricity tariff. |
| **Formula** | Peak Demand × Demand Charge Rate |
| **Unit** | USD |
| **Calculation Frequency** | Monthly |
| **Target** | Minimize |
| **Data Source** | Tariff Database |
| **Primary Users** | Executive |

---

## KPI 44 — Grid Import

| Field | Value |
|------|------|
| **KPI Name** | Grid Import |
| **Abbreviation** | GI |
| **Definition** | Total electrical energy imported from the grid during the reporting period. |
| **Formula** | Sum(Imported Energy) |
| **Unit** | MWh |
| **Calculation Frequency** | Daily |
| **Target** | Informational |
| **Data Source** | Revenue Meter |
| **Primary Users** | Operations Manager |

---

## KPI 45 — Grid Export

| Field | Value |
|------|------|
| **KPI Name** | Grid Export |
| **Abbreviation** | GE |
| **Definition** | Total electrical energy exported to the utility grid. Represents revenue-generating production. |
| **Formula** | Sum(Exported Energy) |
| **Unit** | MWh |
| **Calculation Frequency** | Daily |
| **Target** | Maximize |
| **Data Source** | Revenue Meter |
| **Primary Users** | Executive |

---

## KPI 46 — Voltage Compliance

| Field | Value |
|------|------|
| **KPI Name** | Voltage Compliance |
| **Abbreviation** | VC |
| **Definition** | Percentage of time plant voltage remains within allowable grid code limits. |
| **Formula** | Compliant Intervals ÷ Total Intervals ×100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | ≥99% |
| **Data Source** | SCADA |
| **Primary Users** | Engineer |

---

## KPI 47 — Frequency Compliance

| Field | Value |
|------|------|
| **KPI Name** | Frequency Compliance |
| **Abbreviation** | FC |
| **Definition** | Percentage of time grid frequency remains within regulatory limits. |
| **Formula** | Compliant Frequency Intervals ÷ Total Intervals ×100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | ≥99.9% |
| **Data Source** | Protection Relay, SCADA |
| **Primary Users** | Engineer |

---

## KPI 48 — Grid Stability Index

| Field | Value |
|------|------|
| **KPI Name** | Grid Stability Index |
| **Abbreviation** | GSI |
| **Definition** | Composite indicator measuring voltage, frequency, and grid event stability across the reporting period. |
| **Formula** | Weighted Stability Score |
| **Unit** | Score (0–100) |
| **Calculation Frequency** | Daily |
| **Target** | >95 |
| **Data Source** | SCADA, Grid Events |
| **Primary Users** | Executive, Engineer |

---

# End of Part 3

The next section contains:

- Lost Energy Value
- Revenue at Risk
- Maintenance Cost per Asset
- Cost per Incident
- Avoidable Outage Cost
- Cost per MWh
- Savings Opportunity
- Payback Period
- ROI
- Budget Variance
- Forecast Revenue
- Financial Performance KPIs

# Financial KPIs

---

## KPI 49 — Lost Energy Value

| Field | Value |
|------|------|
| **KPI Name** | Lost Energy Value |
| **Abbreviation** | LEV |
| **Definition** | Estimated monetary value of electrical energy that could not be generated or exported due to outages, equipment failures, curtailment, or operational inefficiencies. |
| **Formula** | Lost Energy (MWh) × Energy Tariff |
| **Unit** | USD |
| **Calculation Frequency** | Daily, Monthly |
| **Target** | Minimize |
| **Data Source** | SCADA, Tariff Database |
| **Primary Users** | Executive, Finance |

---

## KPI 50 — Revenue at Risk

| Field | Value |
|------|------|
| **KPI Name** | Revenue at Risk |
| **Abbreviation** | RAR |
| **Definition** | Estimated revenue exposure caused by current operational risks, including outages, degraded equipment, and forecasted failures. |
| **Formula** | Σ(Expected Revenue Losses) |
| **Unit** | USD |
| **Calculation Frequency** | Daily |
| **Target** | Minimize |
| **Data Source** | Analytics Engine |
| **Primary Users** | Executive |

---

## KPI 51 — Maintenance Cost per Asset

| Field | Value |
|------|------|
| **KPI Name** | Maintenance Cost per Asset |
| **Abbreviation** | MCPA |
| **Definition** | Average maintenance expenditure incurred for each monitored asset during the reporting period. |
| **Formula** | Total Maintenance Cost ÷ Number of Assets |
| **Unit** | USD/Asset |
| **Calculation Frequency** | Monthly |
| **Target** | Optimize |
| **Data Source** | CMMS |
| **Primary Users** | Executive, Plant Engineer |

---

## KPI 52 — Cost per Incident

| Field | Value |
|------|------|
| **KPI Name** | Cost per Incident |
| **Abbreviation** | CPI |
| **Definition** | Average financial impact associated with each operational incident, including labour, replacement parts, lost generation, and downtime. |
| **Formula** | Total Incident Cost ÷ Number of Incidents |
| **Unit** | USD |
| **Calculation Frequency** | Monthly |
| **Target** | Reduce |
| **Data Source** | Incident Database |
| **Primary Users** | Executive |

---

## KPI 53 — Cost per MWh Generated

| Field | Value |
|------|------|
| **KPI Name** | Cost per MWh Generated |
| **Abbreviation** | CPM |
| **Definition** | Average operational cost required to produce one megawatt-hour of electricity. |
| **Formula** | Total Operating Cost ÷ Total Energy Generated |
| **Unit** | USD/MWh |
| **Calculation Frequency** | Monthly |
| **Target** | Minimize |
| **Data Source** | Financial System |
| **Primary Users** | Executive |

---

## KPI 54 — Avoidable Outage Cost

| Field | Value |
|------|------|
| **KPI Name** | Avoidable Outage Cost |
| **Abbreviation** | AOC |
| **Definition** | Estimated financial loss caused by outages that could have been prevented through predictive maintenance or operational improvements. |
| **Formula** | Σ(Avoidable Lost Revenue + Maintenance Cost) |
| **Unit** | USD |
| **Calculation Frequency** | Monthly |
| **Target** | Zero |
| **Data Source** | Analytics Engine |
| **Primary Users** | Executive |

---

## KPI 55 — Estimated Annual Savings Opportunity

| Field | Value |
|------|------|
| **KPI Name** | Estimated Annual Savings Opportunity |
| **Abbreviation** | EASO |
| **Definition** | Estimated annual financial benefit achievable by implementing all recommended operational improvements. |
| **Formula** | Σ(Recommendation Savings) |
| **Unit** | USD |
| **Calculation Frequency** | Monthly |
| **Target** | Maximize |
| **Data Source** | Recommendation Engine |
| **Primary Users** | Executive |

---

## KPI 56 — Recommendation ROI

| Field | Value |
|------|------|
| **KPI Name** | Recommendation Return on Investment |
| **Abbreviation** | ROI |
| **Definition** | Estimated financial return generated by implementing a recommendation compared to its implementation cost. |
| **Formula** | (Benefit − Cost) ÷ Cost ×100 |
| **Unit** | % |
| **Calculation Frequency** | Per Recommendation |
| **Target** | >20% |
| **Data Source** | Cost Optimization Model |
| **Primary Users** | Executive |

---

## KPI 57 — Payback Period

| Field | Value |
|------|------|
| **KPI Name** | Payback Period |
| **Abbreviation** | PP |
| **Definition** | Estimated time required for an operational improvement to recover its implementation cost through realized savings. |
| **Formula** | Investment Cost ÷ Annual Savings |
| **Unit** | Months |
| **Calculation Frequency** | Per Recommendation |
| **Target** | <24 Months |
| **Data Source** | Financial Analysis |
| **Primary Users** | Executive |

---

## KPI 58 — Budget Variance

| Field | Value |
|------|------|
| **KPI Name** | Budget Variance |
| **Abbreviation** | BV |
| **Definition** | Difference between planned budget and actual operational expenditure. |
| **Formula** | Actual Cost − Budget |
| **Unit** | USD |
| **Calculation Frequency** | Monthly |
| **Target** | Within ±5% |
| **Data Source** | Finance Database |
| **Primary Users** | Executive |

---

## KPI 59 — Forecast Revenue

| Field | Value |
|------|------|
| **KPI Name** | Forecast Revenue |
| **Abbreviation** | FR |
| **Definition** | Estimated future revenue based on forecast energy generation and applicable tariffs. |
| **Formula** | Forecast Generation × Tariff |
| **Unit** | USD |
| **Calculation Frequency** | Daily |
| **Target** | Meet Budget |
| **Data Source** | Forecast Model |
| **Primary Users** | Executive |

---

## KPI 60 — Budget Achievement

| Field | Value |
|------|------|
| **KPI Name** | Budget Achievement |
| **Abbreviation** | BA |
| **Definition** | Percentage of budgeted generation or revenue achieved during the reporting period. |
| **Formula** | Actual ÷ Budget ×100 |
| **Unit** | % |
| **Calculation Frequency** | Monthly |
| **Target** | ≥100% |
| **Data Source** | Budget Database |
| **Primary Users** | Executive |

---

## KPI 61 — Maintenance ROI

| Field | Value |
|------|------|
| **KPI Name** | Maintenance ROI |
| **Abbreviation** | MROI |
| **Definition** | Measures the financial benefit generated from maintenance investments relative to maintenance expenditure. |
| **Formula** | Avoided Losses ÷ Maintenance Cost |
| **Unit** | Ratio |
| **Calculation Frequency** | Quarterly |
| **Target** | >2 |
| **Data Source** | Maintenance + Finance |
| **Primary Users** | Executive, Plant Engineer |

---

## KPI 62 — Portfolio Profitability Index

| Field | Value |
|------|------|
| **KPI Name** | Portfolio Profitability Index |
| **Abbreviation** | PPI |
| **Definition** | Composite financial indicator measuring operational profitability across all plants using weighted revenue, cost, and availability metrics. |
| **Formula** | Weighted Financial Score |
| **Unit** | Score (0–100) |
| **Calculation Frequency** | Monthly |
| **Target** | >90 |
| **Data Source** | Analytics Engine |
| **Primary Users** | Executive |

---

# End of Part 4

The next section contains:

- Telemetry Completeness
- Sensor Validity
- Communication Availability
- Data Freshness
- Duplicate Rate
- Missing Data Rate
- ETL Success Rate
- Pipeline Health
- Data Quality Score
- Model Version Tracking
- KPI Governance
- KPI Calculation Standards

This is the final section of the KPI Dictionary.

# Data Quality & Platform Governance KPIs

---

## KPI 63 — Telemetry Completeness

| Field | Value |
|------|------|
| **KPI Name** | Telemetry Completeness |
| **Abbreviation** | TC |
| **Definition** | Percentage of expected SCADA telemetry records successfully received during the reporting period. Missing records may indicate communication failures, equipment issues, or ETL problems. |
| **Formula** | Received Records ÷ Expected Records ×100 |
| **Unit** | % |
| **Calculation Frequency** | Hourly, Daily |
| **Target** | ≥99.5% |
| **Data Source** | SCADA |
| **Primary Users** | Platform Administrator, Operations Manager |

---

## KPI 64 — Sensor Validity

| Field | Value |
|------|------|
| **KPI Name** | Sensor Validity |
| **Abbreviation** | SV |
| **Definition** | Percentage of sensor readings that pass engineering validation rules including acceptable operating ranges and physical consistency. |
| **Formula** | Valid Readings ÷ Total Readings ×100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | ≥99% |
| **Data Source** | SCADA |
| **Primary Users** | Platform Administrator |

---

## KPI 65 — Communication Availability

| Field | Value |
|------|------|
| **KPI Name** | Communication Availability |
| **Abbreviation** | CommAvail |
| **Definition** | Percentage of time communication links between field devices and the central monitoring platform remain operational. |
| **Formula** | Communication Uptime ÷ Total Time ×100 |
| **Unit** | % |
| **Calculation Frequency** | Hourly |
| **Target** | ≥99.8% |
| **Data Source** | RMS |
| **Primary Users** | Operations Manager, Platform Administrator |

---

## KPI 66 — Data Freshness Delay

| Field | Value |
|------|------|
| **KPI Name** | Data Freshness Delay |
| **Abbreviation** | DFD |
| **Definition** | Measures the delay between data generation at the source and successful availability within the analytics platform. |
| **Formula** | Current Time − Latest Available Timestamp |
| **Unit** | Minutes |
| **Calculation Frequency** | Continuous |
| **Target** | <15 Minutes |
| **Data Source** | ETL Audit Logs |
| **Primary Users** | Platform Administrator |

---

## KPI 67 — Duplicate Record Rate

| Field | Value |
|------|------|
| **KPI Name** | Duplicate Record Rate |
| **Abbreviation** | DRR |
| **Definition** | Percentage of duplicate telemetry records detected during ETL processing. |
| **Formula** | Duplicate Records ÷ Total Records ×100 |
| **Unit** | % |
| **Calculation Frequency** | Every ETL Run |
| **Target** | <0.1% |
| **Data Source** | ETL Pipeline |
| **Primary Users** | Platform Administrator |

---

## KPI 68 — Missing Data Rate

| Field | Value |
|------|------|
| **KPI Name** | Missing Data Rate |
| **Abbreviation** | MDR |
| **Definition** | Percentage of expected data unavailable because of communication failures, equipment outages, or ingestion problems. |
| **Formula** | Missing Records ÷ Expected Records ×100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | <0.5% |
| **Data Source** | ETL Validation |
| **Primary Users** | Platform Administrator |

---

## KPI 69 — ETL Success Rate

| Field | Value |
|------|------|
| **KPI Name** | ETL Success Rate |
| **Abbreviation** | ETLSR |
| **Definition** | Percentage of scheduled ETL executions completed successfully without critical failures. |
| **Formula** | Successful Runs ÷ Scheduled Runs ×100 |
| **Unit** | % |
| **Calculation Frequency** | Daily |
| **Target** | ≥99% |
| **Data Source** | ETL Audit Logs |
| **Primary Users** | Platform Administrator |

---

## KPI 70 — Data Quality Pass Rate

| Field | Value |
|------|------|
| **KPI Name** | Data Quality Pass Rate |
| **Abbreviation** | DQPR |
| **Definition** | Percentage of automated validation rules successfully passed during ETL execution. |
| **Formula** | Passed Rules ÷ Total Rules ×100 |
| **Unit** | % |
| **Calculation Frequency** | Every ETL Run |
| **Target** | 100% Critical Rules |
| **Data Source** | Great Expectations |
| **Primary Users** | Platform Administrator |

---

## KPI 71 — Pipeline Execution Time

| Field | Value |
|------|------|
| **KPI Name** | Pipeline Execution Time |
| **Abbreviation** | PET |
| **Definition** | Total elapsed time required for completion of one full ETL pipeline execution. |
| **Formula** | ETL End Time − ETL Start Time |
| **Unit** | Minutes |
| **Calculation Frequency** | Every ETL Run |
| **Target** | <30 Minutes |
| **Data Source** | ETL Audit Logs |
| **Primary Users** | Platform Administrator |

---

## KPI 72 — Database Query Response Time

| Field | Value |
|------|------|
| **KPI Name** | Database Query Response Time |
| **Abbreviation** | DQRT |
| **Definition** | Average execution time required for analytical SQL queries. |
| **Formula** | Total Query Duration ÷ Number of Queries |
| **Unit** | Seconds |
| **Calculation Frequency** | Continuous |
| **Target** | <2 Seconds |
| **Data Source** | PostgreSQL |
| **Primary Users** | Platform Administrator |

---

## KPI 73 — Dashboard Load Time

| Field | Value |
|------|------|
| **KPI Name** | Dashboard Load Time |
| **Abbreviation** | DLT |
| **Definition** | Time required for a Streamlit dashboard page to become fully interactive. |
| **Formula** | Page Render Complete − Request Time |
| **Unit** | Seconds |
| **Calculation Frequency** | Continuous |
| **Target** | <3 Seconds |
| **Data Source** | Streamlit Logs |
| **Primary Users** | Platform Administrator |

---

## KPI 74 — Model Inference Time

| Field | Value |
|------|------|
| **KPI Name** | Model Inference Time |
| **Abbreviation** | MIT |
| **Definition** | Average execution time required for an ML model to generate predictions. |
| **Formula** | Total Prediction Time ÷ Number of Predictions |
| **Unit** | Milliseconds |
| **Calculation Frequency** | Continuous |
| **Target** | <500 ms |
| **Data Source** | ML Pipeline |
| **Primary Users** | Platform Administrator |

---

## KPI 75 — Model Version Compliance

| Field | Value |
|------|------|
| **KPI Name** | Model Version Compliance |
| **Abbreviation** | MVC |
| **Definition** | Confirms that production predictions are generated using the latest approved model version. |
| **Formula** | Approved Version = Active Version |
| **Unit** | Boolean |
| **Calculation Frequency** | Daily |
| **Target** | 100% |
| **Data Source** | Model Registry |
| **Primary Users** | Platform Administrator |

---

## KPI 76 — Recommendation Traceability

| Field | Value |
|------|------|
| **KPI Name** | Recommendation Traceability |
| **Abbreviation** | RT |
| **Definition** | Percentage of recommendations that can be traced back to supporting evidence, source data, and analytical models. |
| **Formula** | Traceable Recommendations ÷ Total Recommendations ×100 |
| **Unit** | % |
| **Calculation Frequency** | Weekly |
| **Target** | 100% |
| **Data Source** | Recommendation Engine |
| **Primary Users** | Executive, Platform Administrator |

---

# KPI Governance Standards

To ensure consistency across the platform, every KPI must comply with the following governance principles:

## Standardization

- Every KPI has a single approved business definition.
- KPI formulas remain version controlled.
- Units of measurement are standardized across all reports.
- KPI calculations are reproducible.

---

## Traceability

Every KPI must identify:

- Source tables
- Source systems
- Calculation logic
- Refresh frequency
- Data owner
- Business owner

---

## Data Quality

KPIs are calculated only after all mandatory validation rules have passed.

Critical validation failures prevent KPI publication.

---

## Version Control

Changes to KPI definitions require:

- Version increment
- Documentation update
- Stakeholder approval
- Git version history

---

## KPI Categories

| Category | Total KPIs |
|------------|-----------:|
| Solar Performance | 15 |
| Reliability & Operations | 20 |
| Load & Demand | 13 |
| Financial | 14 |
| Data Quality & Platform | 14 |

---

# Summary

The Energy Operations Intelligence Platform includes **76 standardized KPIs** spanning engineering performance, operational reliability, energy production, financial performance, load management, data quality, and platform governance.

Every KPI is fully documented with:

- Business definition
- Engineering calculation
- Formula
- Unit of measure
- Refresh frequency
- Performance target
- Data source
- Primary stakeholder

This KPI Dictionary serves as the authoritative reference for all dashboards, SQL analytics, machine learning models, executive reports, and operational decision-support capabilities within the platform.

---

**End of Document**
