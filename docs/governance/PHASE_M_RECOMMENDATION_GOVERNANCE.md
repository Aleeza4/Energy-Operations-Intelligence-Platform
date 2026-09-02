# Phase M recommendation governance

Phase M establishes evidence-safe contracts for recommendation identity,
lifecycle, ownership, evidence, audit events, financial assumptions, and
financial calculations. It does not claim that the current in-process demo
provider is durable workflow storage.

## Governance contract

Every governed value is classified as `OBSERVED`, `DERIVED`, `CONFIGURED`,
`USER_ENTERED`, `MODEL_OUTPUT`, `REPRESENTATIVE_SYNTHETIC`, or `UNAVAILABLE`.
Existing application recommendations are representative demo records. They
initialize as `PROPOSED` (`CONFIGURED`) with owner `Unassigned`
(`UNAVAILABLE`); neither value represents historical review activity.

Recommendation IDs are SHA-256-derived from immutable source-system and source
record identity, not row position. Sorting and filtering therefore do not alter
identity. The application export is an adapter over the central governance
domain model and includes source identity, classifications, evidence semantics,
assumption availability, and financial availability.

## Lifecycle, ownership, and authorization

Allowed transitions are:

- `PROPOSED` -> `UNDER_REVIEW` or `CANCELLED`
- `UNDER_REVIEW` -> `APPROVED`, `DEFERRED`, `REJECTED`, or `CANCELLED`
- `DEFERRED` -> `UNDER_REVIEW` or `CANCELLED`
- `APPROVED` -> `IN_PROGRESS` or `CANCELLED`
- `IN_PROGRESS` -> `COMPLETED` or `CANCELLED`

Rejected, completed, and cancelled states are terminal. Duplicate, invalid, and
backdated transitions fail explicitly. Assignment is optional; an assignment
must provide an owner identifier, display name, and functional role and is
classified `USER_ENTERED`. Viewer writes are rejected; operator and admin
actors may exercise the domain boundary. No write endpoints or decorative UI
workflow controls are exposed because durable persistence is not verified.

Audit events are immutable and append-oriented. They preserve recommendation
ID, prior and new values, actor identity and role, UTC occurrence time, and an
optional note. Status changes, owner assignment, and review notes are supported.
Actor identity is never synthesized by the domain model.

## Evidence and relationship semantics

Evidence references preserve evidence type, source system, source record ID,
asset attribution, timestamp when available, classification, description, and
relationship strength. Exact plant/equipment identity may support `RELATED_TO`;
it does not establish `DERIVED_FROM`, `TRIGGERED_BY`, or `CAUSED_BY`.

The demo anomaly references are `REPRESENTATIVE_SYNTHETIC` and `RELATED_TO`.
Recommendations without an exact referenced record remain `UNAVAILABLE`. No
incident, maintenance, forecast, work-order, approval, rejection, or completion
linkage is inferred.

## Financial semantics

| Existing field | Actual meaning | Classification | Currency known? | Formula known? | Phase M treatment |
|---|---|---|---|---|---|
| Recoverable Energy | Representative technical energy opportunity | `REPRESENTATIVE_SYNTHETIC` | Not applicable | Source quantity only | Preserve in kWh; never call it money |
| Financial Impact | Legacy presentation concept without traceable inputs | `UNAVAILABLE` | No | No | Withhold amount |
| Recoverable Opportunity | Previously ambiguous monetary aggregation | `UNAVAILABLE` | No | No | Executive UI states conversion is unavailable |
| ROI | Benefit/cost ratio requiring both inputs | `UNAVAILABLE` | No | Contract formula only | Withhold until benefit and investment cost exist |
| Revenue at Risk | Future production-revenue exposure | `UNAVAILABLE` | No | Contract formula only | `NOT VERIFIED` for current records |

Versioned financial assumptions have no silent defaults. A monetary output
requires the relevant quantity, price or cost basis, currency, horizon,
assumption version, formula, and source classifications. Test-only values may be
`REPRESENTATIVE_SYNTHETIC`; they do not become application facts.

Revenue at Risk is defined for this contract as future production-revenue
exposure:

```text
energy_at_risk_mwh * energy_sale_price_per_mwh
```

This does not rename historical variance or recoverable energy. The current
application has no approved future energy-at-risk quantity, sale price,
currency, or horizon. Its status is therefore `NOT VERIFIED`.

| Concept | Definition | Required inputs | Available inputs | Currency | Horizon | Status |
|---|---|---|---|---|---|---|
| Revenue at Risk | Future revenue exposure from energy genuinely at risk | Future energy at risk, approved price, currency, horizon, version, provenance | Calculation contract only; representative recoverable energy is not future exposure | Unavailable | Unavailable | `NOT VERIFIED` |

The Phase L maintenance model is not used for probability-weighted money. Its
PR-AUC, ROC-AUC, precision, and top-5% recall criteria failed. Forecast MAE,
WAPE, and interval-coverage failures also remain visible.

ROI uses `((benefit - investment_cost) / investment_cost) * 100`, but current
benefit and investment-cost inputs are unavailable. Realized benefit is `NOT
VERIFIED`; it requires completed action, post-action observation, a comparison
methodology, and attributable measurement.

## Capability status

| Capability | Phase M implementation | Persistence | Authorization | Evidence | Status |
|---|---|---|---|---|---|
| Stable ID | Deterministic source identity hash | Reproducible | Read | Source system and record ID | `PASS` |
| Owner | Optional typed assignment; defaults unassigned | In-memory boundary only | Operator/admin | User-entered audit event | `PARTIAL` |
| Lifecycle | Controlled states and transitions | In-memory boundary only | Operator/admin | Append-only events | `PARTIAL` |
| Audit history | Immutable UTC events; chronological append validation | In-memory boundary only | Operator/admin writes | Actor and prior/new values | `PARTIAL` |
| Evidence reference | Typed source and explicit relationship | Exported with recommendation | Read | Synthetic demo references only | `PASS` |
| Provenance | Required source classification | Exported | Read | Per-value classifications | `PASS` |
| Financial assumptions | Typed, versioned, no defaults | No approved registry values | Admin configuration not exposed | Missing inputs explicit | `PARTIAL` |
| Currency | Required for monetary calculation | Unavailable | Not applicable | No approved currency | `PARTIAL` |
| Revenue at Risk | Reproducible formula boundary | No calculation persisted | Not applicable | Required inputs absent | `NOT VERIFIED` |
| Realized benefit | Definition and evidence gate only | None | Not applicable | Completion/post-action data absent | `NOT VERIFIED` |
| ROI | Reproducible formula boundary | No calculation persisted | Not applicable | Benefit and cost absent | `NOT VERIFIED` |
| Exports | Analytical, governance, evidence, and financial fields separated | CSV snapshot | Read | Classifications included | `PASS` |

## Persistence and API limitations

The existing recommendation API remains read-only. Governance write endpoints
were intentionally not added because Phase L could not verify database runtime
or durable recommendation storage. The domain contract, authorization rules,
append-only behavior, and serialization are testable; durable workflow
execution remains `PARTIAL`. Database runtime certification remains outside
Phase M.
