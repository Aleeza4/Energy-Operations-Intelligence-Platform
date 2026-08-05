# EOIP Architecture Decision Log (ADR)

> Purpose:
> Record important architectural and technical decisions made during the project.
>
> Rule:
> Every significant design change should be documented here before implementation.

---

## ADR-001

### Decision
Use a phased architecture for EOIP.

### Reason
Keeps implementation modular, testable, and easier to manage.

### Status
Accepted

---

## ADR-002

### Decision
Every production file must have a corresponding unit test.

### Reason
Maintain high code quality and long-term maintainability.

### Status
Accepted

---

## ADR-003

### Decision
Use Ruff, Black, and Pytest as mandatory quality gates.

### Reason
Ensure consistent style and reliable testing.

### Status
Accepted

---

## ADR-004

### Decision
Maintain a File Registry as the single source of truth for implementation status.

### Reason
Prevent duplicate files, repeated work, and confusion.

### Status
Accepted

---

# Template for New Decisions

## ADR-XXX

### Decision

### Reason

### Alternatives Considered

### Impact

### Status