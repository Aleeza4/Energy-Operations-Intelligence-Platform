# Assumptions & Limitations

**Project:** Energy Operations Intelligence Platform (EOIP)
**Document:** Assumptions & Limitations
**Version:** 1.0
**Status:** Draft
**Prepared By:** Energy Analytics Consultant

---

# Purpose

This document defines the engineering assumptions, analytical assumptions, deployment assumptions, and known limitations associated with the Energy Operations Intelligence Platform (EOIP).

The platform is built using a **physics-informed synthetic dataset** designed to emulate realistic utility-scale solar operations while avoiding the use of confidential operational data.

The objective of this document is to clearly distinguish between:

- Engineering assumptions
- Data generation assumptions
- Machine learning assumptions
- Infrastructure assumptions
- Known project limitations

This ensures transparency, reproducibility, and appropriate interpretation of analytical results.

---

# 1. Engineering Assumptions

The synthetic operational dataset is designed to preserve realistic engineering relationships observed in utility-scale photovoltaic (PV) power plants.

## 1.1 Solar Generation

The simulation assumes that electrical generation is primarily influenced by:

- Plane of Array (POA) Irradiance
- Ambient Temperature
- Module Temperature
- Installed DC Capacity
- Inverter Conversion Efficiency
- Equipment Availability
- Grid Availability

Generation follows expected photovoltaic production characteristics, including:

- Zero generation during nighttime.
- Peak generation around solar noon.
- Seasonal variation in irradiance.
- Weather-dependent production.
- Reduced production under cloud cover.

---

## 1.2 Equipment Performance

Equipment is assumed to operate within manufacturer specifications under normal operating conditions.

Equipment degradation occurs gradually through:

- Thermal stress
- Equipment aging
- Repeated operational faults
- Environmental exposure

Major equipment types include:

- String Inverters
- Central Inverters
- Transformers
- Weather Stations
- Revenue Meters
- Protection Relays

---

## 1.3 Weather Relationships

Weather observations are generated using correlated variables.

The model assumes:

- Higher irradiance generally increases production.
- High module temperature decreases conversion efficiency.
- Increased cloud cover reduces irradiance.
- Wind speed reduces module temperature.
- Seasonal weather follows historical climatic trends.

Random weather behaviour is introduced while maintaining realistic physical relationships.

---

## 1.4 Grid Behaviour

Grid events include:

- Planned outages
- Unplanned outages
- Export limitations
- Curtailment requests

Grid availability is treated independently from equipment availability.

Plants may remain technically available while unable to export electricity due to external grid constraints.

---

## 1.5 Maintenance Effects

Maintenance activities are assumed to improve equipment condition.

Corrective maintenance may:

- Restore inverter efficiency.
- Reduce failure probability.
- Improve equipment health score.

Preventive maintenance is assumed to reduce future operational risk.

---

# 2. Synthetic Data Assumptions

## 2.1 Purpose of Synthetic Data

The synthetic dataset is intended to demonstrate analytical methodologies rather than reproduce any specific customer environment.

No proprietary operational data has been used.

No confidential customer information is included.

---

## 2.2 Physics-Informed Relationships

The simulation preserves realistic relationships including:

- Irradiance → Power Output
- Temperature → Efficiency Loss
- Equipment Failure → Reduced Generation
- Grid Outage → Zero Export
- Maintenance → Improved Reliability
- Fault Frequency → Higher Failure Risk
- Repeated Alarms → Increased Operational Priority

---

## 2.3 Random Sampling

Certain variables are generated using controlled statistical distributions.

Examples include:

- Failure occurrence
- Alarm frequency
- Repair duration
- Technician availability
- Weather variability
- Component aging
- Communication failures

Random generation follows predefined probability distributions to maintain realistic operational diversity.

---

## 2.4 Injected Operational Scenarios

The simulation intentionally includes representative operational events, including:

- Inverter failure
- Transformer overheating
- Communication loss
- Grid outage
- Curtailment
- Sensor drift
- Sensor freeze
- Alarm storms
- Thermal derating
- Soiling accumulation
- Equipment degradation
- Planned maintenance
- Corrective maintenance
- Repeated equipment failures

These scenarios provide realistic training and evaluation data for analytics and machine learning models.

---

## 2.5 Ground Truth Labels

Injected operational events are stored as ground truth.

These labels support:

- Forecast evaluation
- Anomaly detection evaluation
- Predictive maintenance validation
- Recommendation validation

Ground truth is available only because the dataset is synthetic.

---

# 3. Analytical Assumptions

## 3.1 Forecasting

Forecasting models assume that future behaviour is influenced by historical observations.

Features include:

- Historical generation
- Irradiance
- Temperature
- Day of Week
- Month
- Season
- Rolling averages
- Lag features

Forecast models are evaluated against baseline methods before deployment.

---

## 3.2 Anomaly Detection

Anomalies are assumed to represent statistically unusual operational behaviour.

Not every anomaly represents a failure.

Anomalies may indicate:

- Sensor faults
- Communication issues
- Equipment degradation
- Grid events
- Environmental conditions

Operational review remains necessary before maintenance decisions are made.

---

## 3.3 Predictive Maintenance

Failure prediction assumes that future equipment failures are influenced by:

- Historical fault frequency
- Equipment age
- Maintenance history
- Operational loading
- Temperature exposure
- Historical availability

Predicted failure probability should support maintenance planning rather than replace engineering judgement.

---

## 3.4 Equipment Health Score

Equipment health is represented as a composite index combining:

- Performance
- Reliability
- Fault history
- Maintenance history
- Operational efficiency
- Data quality

The score is intended as a decision-support indicator rather than a direct engineering measurement.

---

## 3.5 Cost Optimization

Financial optimization assumes:

- Stable tariff structures
- Known maintenance costs
- Estimated outage costs
- Estimated energy prices

Scenario analysis provides decision support rather than financial guarantees.

---

# 4. Machine Learning Assumptions

The platform assumes:

- Historical patterns provide predictive value.
- Training data is representative.
- Input variables remain statistically consistent.
- Data drift remains within acceptable limits.
- Models are periodically retrained.

Models included in the platform include:

- Prophet
- Isolation Forest
- XGBoost / LightGBM
- Random Forest
- Logistic Regression

Future model upgrades may incorporate deep learning where justified by measurable performance improvements.

---

# 5. Data Quality Assumptions

The analytics platform assumes that:

- All timestamps are synchronized to UTC.
- Equipment identifiers remain unique.
- Sensor units remain standardized.
- Duplicate records are removed.
- Missing values are handled during ETL.
- Invalid observations are quarantined before loading.

Critical validation failures prevent publication of downstream analytics.

---

# 6. Infrastructure Assumptions

The platform assumes deployment using:

- Python
- PostgreSQL
- TimescaleDB
- Streamlit
- Docker

The analytical environment assumes:

- Approximately 17 million SCADA records.
- Twelve months of telemetry.
- Fifteen-minute sampling intervals.
- Incremental ETL processing.
- Indexed database tables.
- Continuous aggregate tables for dashboard queries.

---

# 7. Performance Assumptions

The platform is designed with the following performance objectives:

| Metric | Target |
|---------|--------|
| ETL Completion | <30 minutes |
| Executive Dashboard Load Time | <3 seconds |
| Aggregate SQL Query | <2 seconds |
| Raw Time-Series Query | <10 seconds |
| Model Prediction | <500 milliseconds |

These targets are based on portfolio-scale analytical workloads rather than enterprise production environments.

---

# 8. Project Limitations

The platform has several intentional limitations.

## 8.1 Synthetic Data

Although engineering relationships are realistic, synthetic data cannot reproduce every operational characteristic observed in commercial solar portfolios.

Operational behaviour should therefore be interpreted as representative rather than historical.

---

## 8.2 Real-Time Operations

The project does not implement live:

- SCADA integration
- OPC-UA communication
- MQTT streaming
- IoT device connectivity
- Enterprise alarm systems

Operational data is simulated.

---

## 8.3 Commercial Systems

The platform does not integrate with:

- SAP PM
- IBM Maximo
- Oracle Utilities
- AVEVA PI
- OSIsoft PI
- SCADA vendor software

Future integration would require customer-specific interfaces.

---

## 8.4 Forecast Accuracy

Forecasting performance depends on:

- Weather quality
- Equipment behaviour
- Data completeness
- Feature engineering

Forecasts should support planning rather than guarantee future production.

---

## 8.5 Predictive Maintenance

Predicted failure probabilities represent statistical estimates.

Maintenance decisions should always consider:

- Engineering inspection
- Manufacturer guidance
- Operational constraints
- Safety procedures

---

## 8.6 Financial Estimates

Financial calculations represent analytical estimates.

Actual financial performance depends upon:

- Market tariffs
- Operational strategy
- Contract terms
- Weather conditions
- Regulatory requirements

---

## 8.7 Scalability

The project demonstrates portfolio-scale analytics.

Enterprise deployments may require:

- Distributed compute
- Cloud-native architecture
- Load balancing
- High-availability databases
- Multi-region deployment

---

# 9. Future Enhancements

Future production implementations may include:

- Live SCADA integration
- MQTT streaming
- Real-time anomaly detection
- Battery Energy Storage System (BESS) analytics
- Wind farm analytics
- Carbon emissions reporting
- Digital twin integration
- GIS visualization
- AI-assisted maintenance planning
- Enterprise authentication
- Multi-tenant architecture

---

# 10. Conclusion

The Energy Operations Intelligence Platform has been intentionally designed as a production-inspired analytics platform that balances engineering realism with practical implementation.

The assumptions documented within this report ensure transparency, reproducibility, and consistent interpretation of analytical results. While the dataset is synthetic, it preserves realistic operational relationships that enable robust development, testing, and demonstration of modern energy analytics techniques.

The platform is intended to demonstrate how engineering expertise, operational analytics, and machine learning can be integrated into a unified decision-support solution. It should be viewed as a strong foundation for future deployment using real operational data within a commercial energy environment.
