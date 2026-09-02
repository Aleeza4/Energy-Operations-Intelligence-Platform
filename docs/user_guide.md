# EOIP User Guide

## 1. Purpose

This user guide describes how to use the Energy Operations Intelligence Platform (EOIP) in its current demonstration and analytical configuration. The platform is designed to support operational oversight, performance review, maintenance prioritization, and executive-level monitoring using representative synthetic data and analytics outputs.

This guide is intentionally written for practical use rather than as a system administrator manual. It focuses on what users can do in the application, how to interpret its outputs, and which limitations must be understood during use.

---

## 2. Who This Guide Is For

This guide is useful for:

- plant operators reviewing plant performance and event context
- engineering teams investigating equipment health and maintenance priorities
- portfolio managers looking for generation and operational performance trends
- stakeholders evaluating the current demonstration outputs and evidence-backed narrative

---

## 3. Entry Points and Access

The platform is delivered through the Streamlit application and includes a structured navigation experience with role-aware operational workflows.

Typical access flow:

1. Start the app from the project environment.
2. Select a plant or equipment scope using the sidebar filters.
3. Navigate to the relevant page for overview, operations, intelligence, or administration.
4. Drill into details when the dashboard highlights anomalies, incidents, or recommendations.

---

## 4. Dashboard Structure

The application groups functionality into a few high-level sections.

### 4.1 Overview

The Overview section is intended to answer high-level portfolio questions such as:

- how generation compares with plan or expectation
- which plants require attention
- which operating issues deserve priority review

This section is best used for rapid executive or portfolio-level diagnosis.

### 4.2 Operations

The Operations section focuses on plant state and operational context. It includes:

- generation and performance status
- maintenance and operational attention signals
- event and alert summaries
- plant and asset operating context

This is the best section for an operator or plant manager reviewing current operating conditions.

### 4.3 Intelligence

The Intelligence section includes the analytic outputs of the project:

- forecasts
- anomaly signals
- maintenance risk views
- recommendation center

These views are intended for insight support and investigation, but they should be interpreted with the project’s documented model limitations in mind.

### 4.4 Platform and Administration

This section includes application configuration, data quality context, and safe system metadata. It is not a live operational control plane and should not be treated as a production governance portal.

---

## 5. How to Use the Main Views

## 5.1 Portfolio Overview

Use this page to:

- compare actual and expected energy output
- identify plants requiring follow-up
- review operational priorities and attention queues

Interpretation guidance:

- a variance signal may indicate weather or performance differences
- the page should be read alongside plant and equipment drill-downs
- do not treat a single KPI as proof of equipment failure without additional context

---

## 5.2 Plant Performance

Use this page to:

- review generation efficiency and performance across plants
- compare actual vs expected output
- assess availability and capacity-factor context

Interpretation guidance:

- performance variance can indicate generation losses, maintenance need, or weather sensitivity
- use related pages for alarms, incidents, and maintenance priorities for a fuller picture

---

## 5.3 Asset Dashboard

Use this page to:

- inspect asset-level health and risk context
- identify equipment with elevated attention needs
- connect operational issues to maintenance recommendations

Interpretation guidance:

- asset health is a decision-support signal, not a guaranteed equipment diagnosis
- field investigation should confirm any operational action

---

## 5.4 Alarms and Incidents

Use this page to:

- review event timelines and current operational severity
- inspect how alarms and incidents relate to plant conditions
- connect actions to maintenance and operational workflows

Interpretation guidance:

- alarm and incident records should be reviewed together rather than in isolation
- event presence indicates operational relevance, not necessarily a confirmed root cause

---

## 5.5 Forecast View

Use this page to:

- view expected generation patterns over a forecast horizon
- compare forecasted output against operational context
- identify periods of potential underperformance or volatility

Interpretation guidance:

- forecast outputs are decision-support information only
- the current project evidence shows mixed forecast performance and should not be treated as a guaranteed production forecast

---

## 5.6 Anomaly View

Use this page to:

- identify unusual operational patterns
- review anomaly severity and contributing factors
- investigate whether a signal requires further operational review

Interpretation guidance:

- anomalies are investigation signals, not confirmed failure events
- anomaly scores should be cross-checked with alarms, incidents, and equipment condition views

---

## 5.7 Maintenance View

Use this page to:

- understand equipment risk and maintenance priority ranking
- identify candidate assets for inspection or service work
- link maintenance attention to plant performance issues

Interpretation guidance:

- maintenance prioritization is advisory and should be validated by human review
- results reflect the project’s current evidence and not a guaranteed reliability forecast

---

## 5.8 Recommendation Center

Use this page to:

- review proposed actions and their reasoning
- understand evidence, urgency, and operational context behind recommendations
- connect recommendations with underlying plant or equipment conditions

Interpretation guidance:

- recommendations are not approval records
- current workflow status values are demonstration-oriented and need human validation before execution
- financial or ROI claims should not be treated as a confirmed business outcome

---

## 6. Filters and Scope Management

The application supports plant, equipment, and date filters. These filters help keep analysis focused and consistent across related pages.

### Best practices

- begin with a plant or portfolio scope when screening issues
- narrow to a single asset when investigating a specific risk signal
- compare a short date window for operational review before broader trend analysis
- keep filters consistent when moving between overview and drill-down sections

---

## 7. Data and Model Limitations

The current platform is built around representative synthetic data and should be used with clear constraints.

Important limitations include:

- the application is not a live telemetry control system
- operations data is representative and deterministic rather than production operational feed
- forecast, anomaly, maintenance, and health views inherit the project’s validation limitations
- recommendation records are not durable execution approvals
- no real financial or revenue impact is being claimed in this implementation

These constraints are a normal part of a project demonstration and should be known to anyone using the app for decision support.

---

## 8. Recommended Reading Sequence

When using the platform for review, the following order is recommended:

1. Overview page for portfolio health context
2. Plant Performance for operational variance review
3. Alarms and Incidents for event context
4. Asset Dashboard for equipment-level issues
5. Maintenance and Recommendation Center for prioritization and action review
6. Forecast and Anomaly views for additional context and investigation support

This sequence preserves a practical operational workflow from portfolio signal to root-cause investigation.

---

## 9. Practical Guidance for Users

- Treat all analytic views as useful decision-support context.
- Prefer layered review across plant, asset, event, and recommendation data.
- Validate outputs with engineering judgement and field context where needed.
- Maintain a clear distinction between a detected signal and a confirmed issue.
- Keep model and data limitations visible during stakeholder discussion.

---

## 10. Summary

The EOIP user experience is designed to support operational monitoring, plant analysis, maintenance prioritization, and leadership review using a structured dashboard workflow. The platform provides meaningful insight into performance and risk, but it must be used with an awareness of its representative data assumptions and the current evidence status of its intelligence components.
