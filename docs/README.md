# EOIP documentation

This index identifies the canonical documentation for the current repository.
Older project-management and phase documents remain historical records; they
are not the primary source for current capability claims.

| Area | Canonical document | Purpose |
|---|---|---|
| Portfolio entry | [README](../README.md) | Project overview, evidence snapshot, quick start, and limitations |
| Architecture | [System architecture](architecture/SYSTEM_ARCHITECTURE.md) | Runtime boundaries, components, and flows |
| Data | [Data architecture](data/DATA_ARCHITECTURE.md) | Data layers, semantics, and discrepancies |
| Data | [Data dictionary](data/DATA_DICTIONARY.md) | Major entities, identifiers, timestamps, and provenance |
| Application | [Streamlit user guide](app/STREAMLIT_USER_GUIDE.md) | Navigation, pages, filters, and scope |
| API | [API guide](api/API_GUIDE.md) | Authentication, route definitions, errors, and runtime limitation |
| Forecast | [Forecast model card](models/FORECAST_MODEL_CARD.md) | Prophet and Seasonal Naive evidence |
| Anomaly | [Anomaly model card](models/ANOMALY_MODEL_CARD.md) | Detection methods and effectiveness limitations |
| Maintenance | [Maintenance model card](models/MAINTENANCE_MODEL_CARD.md) | Failure-risk evidence and leakage controls |
| Health | [Equipment-health model card](models/EQUIPMENT_HEALTH_MODEL_CARD.md) | Health-score decomposition and confidence limitation |
| Governance | [Recommendation governance](governance/PHASE_M_RECOMMENDATION_GOVERNANCE.md) | Identity, lifecycle, evidence, audit, and finance |
| Evaluation | [Reproducibility](evaluation/REPRODUCIBILITY.md) | Phase L deterministic workflow |
| Evaluation | [Evidence index](evaluation/EVIDENCE_INDEX.md) | Artifact discovery and statuses |
| Testing | [Testing guide](testing/TESTING_GUIDE.md) | Test layers and quality commands |
| Deployment | [Deployment guide](deployment/DEPLOYMENT_GUIDE.md) | Configured local/container architecture and unverified areas |
| Portfolio | [Case study](portfolio/EOIP_CASE_STUDY.md) | Evidence-based engineering narrative |
| Portfolio | [Interview guide](portfolio/INTERVIEW_GUIDE.md) | Technical walkthrough and common questions |

Evidence statuses mean:

- `PASS` / `FAIL`: a stated criterion was empirically evaluated.
- `PARTIAL`: capability exists, but required runtime or evidence is incomplete.
- `NOT VERIFIED`: sufficient evidence does not exist.
- `REPRESENTATIVE_SYNTHETIC`: generated evidence, not production truth.
- `CONFIGURED`: architecture or behavior is defined but not necessarily runtime-certified.
