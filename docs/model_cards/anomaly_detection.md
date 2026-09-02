# Anomaly Detection Model Card

## 1. Model Summary

The anomaly detection capability in the Energy Operations Intelligence Platform is designed to flag unusual operating behavior that may warrant investigation. The system supports multiple detector patterns, including statistical and unsupervised methods, but the important operational framing is that an anomaly is an investigation signal rather than proof of equipment failure, root cause, or financial loss.

In EOIP, anomaly detection sits in the broader intelligence stack as a monitoring signal that helps users decide whether to inspect plant behavior, compare conditions to expected operating patterns, or validate whether an incident or equipment degradation may be emerging.

---

## 2. Intended Use

This model is intended for:

- identifying unusual deviations from normal plant or equipment behavior
- surfacing operational alerts for human review
- comparing unusual conditions to known alarm and incident patterns
- supporting dashboard-based monitoring and investigation workflows

This model is not intended for:

- claiming a device is definitely faulty without validation
- automatically assigning root cause
- establishing financial or reliability guarantees
- replacing plant operator judgment or maintenance review

---

## 3. Model Type

EOIP includes anomaly detection implementations designed around unsupervised or statistical detection logic, with the benchmarked implementation using a repository Isolation Forest approach. The model consumes numeric time-series operational features and emits anomaly scores or labels based on the detector’s operating logic.

The key principle is that detector outputs are only actionable when interpreted in context. An anomaly may indicate risk, change, or noise; it does not prove an actual failure by itself.

---

## 4. Data and Inputs

### Primary inputs

- SCADA telemetry readings
- equipment and plant operational context
- time-indexed performance metrics
- synthetic benchmark conditions where applicable

### Example signals

- active power output
- interval energy production
- voltage and current readings
- equipment operating state
- performance ratios or residual-based indicators

### Relationship to ground truth

Ground-truth events in the project are deliberately separated from detector execution and are used to validate benchmark conditions rather than to derive the predictions themselves. This preserves a clean evaluation framework.

---

## 5. Evaluation Methodology

The project’s evaluation framework examines anomaly detection under a fixed benchmark condition. The benchmark uses a representative synthetic plant and explicit time windows to test detector behavior in a controlled environment.

### Evaluation focus

The benchmark primarily verifies the false-alert rate, because the evaluated population may contain no eligible positive events. This means the model can be validated for low false-positive behavior while effectiveness indicators like precision and recall remain not verified if no valid positive events are present.

### Key benchmark facts

- evaluation period: fixed benchmark window centered on representative test conditions
- exposure measured in asset-days
- contamination parameter fixed according to benchmark design
- ground-truth events scheduled before detector execution
- model outputs compared against known event exposure under controlled assumptions

---

## 6. Empirical Results

The current benchmark result indicates that the false-alert criterion passes while the model’s broader effectiveness remains unverified.

| Metric | Result | Status |
| --- | ---: | --- |
| False alerts per asset-day | 0.166667 | PASS |
| Precision | unavailable | NOT VERIFIED |
| Recall | unavailable | NOT VERIFIED |
| F1 | unavailable | NOT VERIFIED |
| Critical-event recall | unavailable | NOT VERIFIED |
| Conservative p95 detection delay | unavailable | NOT VERIFIED |

### Interpretation

The anomaly detector shows a low false-positive rate under the benchmark conditions. However, because there were no eligible positive events in the evaluated test set, the model cannot claim a verified ability to recall or prioritize real failures at this stage.

This is a strong reminder that a low false-positive signal is important, but it does not establish actual anomaly effectiveness without positive-event evidence.

---

## 7. Model Performance Status

### Current status

The project status is:

- false-alert criterion: PASS
- effectiveness: NOT VERIFIED

This means the detection model is suitable for operational investigation support and dashboard monitoring, but not yet for strong claims about detection recall, classification quality, or critical-event sensitivity.

---

## 8. Limitations

The anomaly detection model has several material limitations:

- representative synthetic scope
- no eligible positive benchmark events in the evaluated period
- no verified precision or recall under real operational prevalence
- outputs are not root-cause proof
- detector outputs are not direct evidence of failure or lost production

Because of these conditions, detections should be treated as decision-support signals requiring human validation.

---

## 9. Governance and Risk

The model should be governed as a monitoring aid with clear human oversight.

Recommended controls:

- treat all alerts as investigation triggers, not confirmed failure events
- combine anomaly outputs with alarms, incidents, and equipment context
- avoid automated action from anomaly scores alone
- keep evaluation evidence versioned and reproducible
- explicitly document when effectiveness remains unverified

---

## 10. Summary

The EOIP anomaly detection model is useful as a low-noise operational monitoring signal. It demonstrates acceptable false-alert behavior in the benchmark setting, but it does not yet carry a verified claim of effectiveness in identifying real operational events. For that reason, the model is best positioned as part of a broader operational intelligence workflow rather than as a standalone reliability decision system.
