# User Personas

**Project:** Energy Operations Intelligence Platform (EOIP)
**Document:** User Personas
**Version:** 1.0
**Status:** Draft
**Prepared By:** Energy Analytics Consultant

---

# Purpose

This document defines the primary stakeholders who will interact with the Energy Operations Intelligence Platform (EOIP). Each persona represents a distinct operational role with unique responsibilities, business objectives, decision-making requirements, and information needs.

The platform is designed around these personas to ensure that dashboards, KPIs, analytics, and recommendations directly support real operational workflows within a utility-scale solar energy organization.

---

# Persona 1 — Executive / Portfolio Director

## Overview

The Executive or Portfolio Director is responsible for the strategic performance of the renewable energy portfolio. This role focuses on maximizing energy production, protecting revenue, reducing operational risk, and ensuring long-term asset performance across all plants.

Unlike operational users, executives require high-level business intelligence rather than individual equipment details.

---

## Primary Responsibilities

- Oversee portfolio-wide performance
- Monitor financial performance
- Review operational KPIs
- Approve maintenance budgets
- Evaluate capital investments
- Prioritize strategic initiatives
- Review operational risks
- Report performance to senior leadership and investors

---

## Daily Decisions

- Which plants require executive attention?
- Which sites are underperforming financially?
- Which operational risks require investment?
- Are generation targets likely to be achieved?
- Which maintenance activities should receive funding?
- Where is revenue currently at risk?
- Which recommendations deliver the highest return?

---

## Daily Questions

- Which plants generated below expectations?
- How much revenue is currently at risk?
- Which assets have the highest failure probability?
- What are the biggest operational risks?
- Are maintenance investments producing measurable value?
- Is the portfolio meeting annual generation targets?
- Which sites require executive intervention?

---

## Current Pain Points

- Portfolio reports arrive too late.
- Financial impact of operational issues is difficult to quantify.
- Operational information is fragmented across multiple systems.
- Executive reporting requires manual consolidation.
- Root causes are difficult to identify.
- Maintenance priorities are not financially ranked.
- No centralized view of recoverable energy losses.

---

## Success Looks Like

The Executive can:

- View portfolio health within minutes.
- Identify underperforming plants immediately.
- Understand financial exposure.
- Quantify recoverable generation.
- Prioritize investment based on analytics.
- Make informed strategic decisions without requesting additional reports.

---

## Primary KPIs

- Portfolio Generation
- Expected Generation
- Budget Generation
- Performance Ratio
- Capacity Factor
- Technical Availability
- Revenue at Risk
- Recoverable Energy
- Forecast Generation
- Annual Savings Opportunity
- Cost per MWh
- Portfolio MTBF
- Portfolio MTTR

---

## Dashboard Pages

Primary

- Executive Overview
- Strategic Action Center
- Forecasting & Scenarios

Secondary

- Equipment Health

---

# Persona 2 — SOC / Energy Operations Manager

## Overview

The SOC (Security/Systems Operations Center) or Energy Operations Manager oversees the day-to-day operational health of all generating assets.

This role monitors alarms, incidents, communication health, plant availability, and operational service levels.

---

## Primary Responsibilities

- Monitor portfolio operations
- Manage active alarms
- Ensure SLA compliance
- Coordinate incident response
- Escalate critical issues
- Monitor communication health
- Track operational KPIs
- Coordinate with maintenance teams

---

## Daily Decisions

- Which alarms require immediate attention?
- Which incidents should be escalated?
- Which plants have communication failures?
- Which outages have the highest operational impact?
- Which alarms are false positives?
- Which sites require maintenance dispatch?

---

## Daily Questions

- Which critical alarms remain open?
- Which alarms breached SLA?
- Which communication links failed?
- Which incidents are unresolved?
- Which operators require support?
- Are alarm storms occurring?
- Which plants have reduced availability?

---

## Current Pain Points

- Thousands of alarms each month.
- Alarm fatigue.
- Duplicate alarms.
- Difficulty identifying priority incidents.
- Limited operational visibility.
- Manual incident tracking.
- Poor correlation between alarms and financial impact.

---

## Success Looks Like

The Operations Manager can:

- Identify critical alarms instantly.
- Reduce acknowledgement time.
- Eliminate unnecessary alarm investigation.
- Improve operational response.
- Meet operational SLAs.
- Monitor every plant from one interface.

---

## Primary KPIs

- Active Alarms
- Critical Alarms
- Alarm Acknowledgement Time
- Alarm Resolution Time
- SLA Compliance
- Communication Availability
- Technical Availability
- Grid Availability
- Incident Duration
- Alarm Storm Frequency
- MTTA
- MTTR

---

## Dashboard Pages

Primary

- Operations Command Center
- Faults & Outages
- Platform Health

Secondary

- Executive Overview

---

# Persona 3 — Plant Engineer / Maintenance Planner

## Overview

The Plant Engineer is responsible for ensuring equipment reliability and maximizing plant performance through effective maintenance planning and engineering analysis.

Unlike the Operations Manager, this role focuses on long-term asset health rather than real-time incident management.

---

## Primary Responsibilities

- Monitor equipment performance
- Investigate failures
- Plan preventive maintenance
- Reduce repeat failures
- Improve reliability
- Optimize maintenance schedules
- Review engineering trends
- Validate corrective actions

---

## Daily Decisions

- Which equipment requires maintenance?
- Which failures are recurring?
- Which components should be replaced?
- Which maintenance activities have highest priority?
- Which work orders should be scheduled first?
- Which equipment presents unacceptable risk?

---

## Daily Questions

- Which inverters are degrading?
- Which transformers show abnormal behaviour?
- Which maintenance activities reduced failures?
- Which assets have lowest health scores?
- Which failures are becoming more frequent?
- What caused this outage?
- Which maintenance backlog items are most critical?

---

## Current Pain Points

- Maintenance is reactive.
- Root cause analysis is time consuming.
- Failure history is fragmented.
- Priorities are difficult to establish.
- Maintenance effectiveness is difficult to measure.
- Equipment deterioration is difficult to visualize.

---

## Success Looks Like

The Engineer can:

- Predict failures before they occur.
- Prioritize maintenance objectively.
- Reduce repeat failures.
- Improve asset reliability.
- Extend equipment life.
- Reduce unnecessary maintenance.

---

## Primary KPIs

- Equipment Health Score
- Failure Risk
- MTBF
- MTTR
- Repeat Fault Rate
- Maintenance Backlog
- First Time Fix Rate
- Inverter Efficiency
- Performance Ratio Gap
- Thermal Loss
- Soiling Loss
- Curtailment Loss

---

## Dashboard Pages

Primary

- Equipment Health
- Faults & Outages
- Energy Performance

Secondary

- Forecasting

---

# Persona 4 — Data / Platform Administrator

## Overview

The Data or Platform Administrator ensures that the analytics platform remains reliable, secure, and operational.

This persona focuses on infrastructure rather than business performance.

---

## Primary Responsibilities

- Monitor ETL pipelines
- Validate data quality
- Maintain database performance
- Monitor application health
- Manage deployments
- Track model versions
- Ensure data freshness
- Support users

---

## Daily Decisions

- Did ETL complete successfully?
- Are data quality rules passing?
- Is database performance acceptable?
- Are models current?
- Are dashboards using fresh data?
- Is deployment healthy?
- Are backups successful?

---

## Daily Questions

- When was the last ETL run?
- Are quality checks passing?
- Which tables failed validation?
- Is telemetry complete?
- Are models producing predictions?
- Which deployment version is active?
- Are system resources healthy?

---

## Current Pain Points

- Limited pipeline visibility.
- Manual validation.
- Slow troubleshooting.
- Limited deployment monitoring.
- Poor data lineage.
- Difficult model tracking.
- Limited operational observability.

---

## Success Looks Like

The Administrator can:

- Monitor platform health in real time.
- Identify ETL failures immediately.
- Validate data automatically.
- Track every deployment.
- Maintain high platform availability.
- Resolve issues before users notice them.

---

## Primary KPIs

- ETL Success Rate
- Data Freshness
- Telemetry Completeness
- Duplicate Rate
- Data Quality Pass Rate
- Query Response Time
- API Availability
- Dashboard Load Time
- Model Version
- Drift Status
- Pipeline Success Rate

---

## Dashboard Pages

Primary

- Platform Health

Secondary

- Operations Command Center

---

# Persona-to-Dashboard Mapping

| Dashboard Page | Executive | Operations Manager | Plant Engineer | Administrator |
|---------------|:---------:|:------------------:|:--------------:|:-------------:|
| Executive Overview | ✓ | ✓ | | |
| Operations Command Center | | ✓ | | ✓ |
| Equipment Health | | | ✓ | |
| Energy Performance | ✓ | ✓ | ✓ | |
| Faults & Outages | | ✓ | ✓ | |
| Forecasting & Scenarios | ✓ | | ✓ | |
| Strategic Action Center | ✓ | ✓ | ✓ | |
| Platform Health | | ✓ | | ✓ |

---

# Information Hierarchy

The platform follows a layered information architecture:

**Executive**
→ Portfolio Performance → Financial Exposure → Strategic Recommendations

**Operations Manager**
→ Active Alarms → Incident Status → SLA Performance → Operational Priorities

**Plant Engineer**
→ Equipment Health → Failure Analysis → Maintenance Planning → Root Cause Investigation

**Platform Administrator**
→ ETL Health → Data Quality → Infrastructure → Model Governance

---

# Design Principles

The user experience is guided by the following principles:

- Every dashboard is designed around a specific business persona.
- Information is prioritized based on operational importance.
- Critical actions require no more than three clicks.
- KPIs are traceable to validated data sources.
- Recommendations are supported by transparent evidence.
- Technical complexity is hidden from executive users while remaining accessible to engineers and administrators.
- The platform provides a single source of truth for operational, technical, and financial decision-making.

---

# Conclusion

The Energy Operations Intelligence Platform is intentionally designed around the needs of four primary user groups. Each persona has distinct objectives, responsibilities, and decision-making requirements. By tailoring dashboards, KPIs, and recommendations to these roles, the platform ensures that every stakeholder—from executive leadership to operational engineers—can access relevant, timely, and actionable insights without unnecessary complexity.
