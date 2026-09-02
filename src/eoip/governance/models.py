"""Evidence-safe recommendation governance and financial domain models."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class SourceClassification(StrEnum):
    """Required provenance classes for business and governance values."""

    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    CONFIGURED = "CONFIGURED"
    USER_ENTERED = "USER_ENTERED"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    REPRESENTATIVE_SYNTHETIC = "REPRESENTATIVE_SYNTHETIC"
    UNAVAILABLE = "UNAVAILABLE"


class RecommendationStatus(StrEnum):
    """Controlled recommendation lifecycle states."""

    PROPOSED = "PROPOSED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    DEFERRED = "DEFERRED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


ALLOWED_TRANSITIONS: Mapping[RecommendationStatus, frozenset[RecommendationStatus]] = (
    MappingProxyType(
        {
            RecommendationStatus.PROPOSED: frozenset(
                {RecommendationStatus.UNDER_REVIEW, RecommendationStatus.CANCELLED}
            ),
            RecommendationStatus.UNDER_REVIEW: frozenset(
                {
                    RecommendationStatus.APPROVED,
                    RecommendationStatus.DEFERRED,
                    RecommendationStatus.REJECTED,
                    RecommendationStatus.CANCELLED,
                }
            ),
            RecommendationStatus.DEFERRED: frozenset(
                {RecommendationStatus.UNDER_REVIEW, RecommendationStatus.CANCELLED}
            ),
            RecommendationStatus.APPROVED: frozenset(
                {RecommendationStatus.IN_PROGRESS, RecommendationStatus.CANCELLED}
            ),
            RecommendationStatus.IN_PROGRESS: frozenset(
                {RecommendationStatus.COMPLETED, RecommendationStatus.CANCELLED}
            ),
            RecommendationStatus.REJECTED: frozenset(),
            RecommendationStatus.COMPLETED: frozenset(),
            RecommendationStatus.CANCELLED: frozenset(),
        }
    )
)


class EvidenceType(StrEnum):
    ASSET = "ASSET"
    INCIDENT = "INCIDENT"
    ANOMALY = "ANOMALY"
    MAINTENANCE = "MAINTENANCE"
    PLANT_PERFORMANCE = "PLANT_PERFORMANCE"
    FORECAST = "FORECAST"
    DATA_QUALITY = "DATA_QUALITY"
    MODEL_OUTPUT = "MODEL_OUTPUT"


class EvidenceRelationship(StrEnum):
    RELATED_TO = "RELATED_TO"
    DERIVED_FROM = "DERIVED_FROM"
    TRIGGERED_BY = "TRIGGERED_BY"
    CAUSED_BY = "CAUSED_BY"


class AuditEventType(StrEnum):
    STATUS_CHANGED = "STATUS_CHANGED"
    OWNER_ASSIGNED = "OWNER_ASSIGNED"
    REVIEW_NOTE_ADDED = "REVIEW_NOTE_ADDED"


def _required(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty.")
    return normalized


def _aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")
    return value.astimezone(UTC)


def stable_recommendation_id(source_system: str, source_record_id: str) -> str:
    """Return an export-safe stable ID from immutable source identity."""
    source = _required(source_system, "source_system").casefold()
    record = _required(source_record_id, "source_record_id").casefold()
    digest = hashlib.sha256(f"{source}\x1f{record}".encode()).hexdigest()[:16]
    return f"REC-{digest.upper()}"


@dataclass(frozen=True, slots=True)
class RecommendationOwner:
    """Optional user-entered recommendation assignment."""

    owner_id: str | None = None
    display_name: str | None = None
    role: str | None = None
    classification: SourceClassification = SourceClassification.UNAVAILABLE

    def __post_init__(self) -> None:
        populated = (self.owner_id, self.display_name, self.role)
        if all(value is None for value in populated):
            if self.classification is not SourceClassification.UNAVAILABLE:
                raise ValueError("An unassigned owner must be UNAVAILABLE.")
            return
        if any(value is None or not value.strip() for value in populated):
            raise ValueError("Assigned owner fields must all be populated.")
        if self.classification is not SourceClassification.USER_ENTERED:
            raise ValueError("Assigned owner must be USER_ENTERED.")

    @property
    def label(self) -> str:
        return self.display_name or "Unassigned"


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """A typed evidence link whose relationship strength is explicit."""

    evidence_type: EvidenceType
    source_system: str
    source_record_id: str
    relationship: EvidenceRelationship
    classification: SourceClassification
    plant_id: str | None = None
    equipment_id: str | None = None
    observed_at: datetime | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_system", _required(self.source_system, "source_system")
        )
        object.__setattr__(
            self,
            "source_record_id",
            _required(self.source_record_id, "source_record_id"),
        )
        if self.observed_at is not None:
            object.__setattr__(
                self, "observed_at", _aware(self.observed_at, "observed_at")
            )


@dataclass(frozen=True, slots=True)
class GovernanceActor:
    """Authenticated or explicitly system-classified audit actor."""

    actor_id: str
    role: str
    classification: SourceClassification

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor_id", _required(self.actor_id, "actor_id"))
        object.__setattr__(self, "role", _required(self.role, "role").casefold())
        if self.classification not in {
            SourceClassification.USER_ENTERED,
            SourceClassification.CONFIGURED,
        }:
            raise ValueError("Actor classification must be USER_ENTERED or CONFIGURED.")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable append-oriented governance event."""

    recommendation_id: str
    event_type: AuditEventType
    previous_value: str | None
    new_value: str
    actor: GovernanceActor
    occurred_at: datetime
    note: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "recommendation_id",
            _required(self.recommendation_id, "recommendation_id"),
        )
        object.__setattr__(self, "new_value", _required(self.new_value, "new_value"))
        object.__setattr__(self, "occurred_at", _aware(self.occurred_at, "occurred_at"))


@dataclass(frozen=True, slots=True)
class FinancialAssumptions:
    """Versioned configuration inputs; missing inputs never gain defaults."""

    assumption_version: str
    currency: str | None = None
    energy_sale_price_per_mwh: Decimal | None = None
    analysis_horizon: str | None = None
    classification: SourceClassification = SourceClassification.UNAVAILABLE

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assumption_version",
            _required(self.assumption_version, "assumption_version"),
        )
        if (
            self.energy_sale_price_per_mwh is not None
            and self.energy_sale_price_per_mwh < 0
        ):
            raise ValueError("energy_sale_price_per_mwh must not be negative.")
        if self.currency is not None:
            normalized = self.currency.strip().upper()
            if not re.fullmatch(r"[A-Z]{3}", normalized):
                raise ValueError("currency must be a three-letter code.")
            object.__setattr__(self, "currency", normalized)
        available = (
            self.currency is not None
            or self.energy_sale_price_per_mwh is not None
            or self.analysis_horizon is not None
        )
        if available and self.classification not in {
            SourceClassification.CONFIGURED,
            SourceClassification.REPRESENTATIVE_SYNTHETIC,
        }:
            raise ValueError(
                "Populated financial assumptions require an explicit source "
                "classification."
            )


@dataclass(frozen=True, slots=True)
class FinancialCalculation:
    """Reproducible derived amount or an explicit unavailable result."""

    concept: str
    amount: Decimal | None
    currency: str | None
    formula: str
    inputs: Mapping[str, str]
    assumption_version: str | None
    analysis_horizon: str | None
    classification: SourceClassification
    unavailable_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept", _required(self.concept, "concept"))
        object.__setattr__(self, "formula", _required(self.formula, "formula"))
        object.__setattr__(self, "inputs", MappingProxyType(dict(self.inputs)))
        if self.amount is None:
            if self.classification is not SourceClassification.UNAVAILABLE:
                raise ValueError("A missing amount must be UNAVAILABLE.")
            if not self.unavailable_reasons:
                raise ValueError("Unavailable calculations require reasons.")
        elif self.classification is not SourceClassification.DERIVED:
            raise ValueError("A calculated amount must be DERIVED.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "amount": str(self.amount) if self.amount is not None else None,
            "currency": self.currency,
            "formula": self.formula,
            "inputs": dict(self.inputs),
            "assumption_version": self.assumption_version,
            "analysis_horizon": self.analysis_horizon,
            "classification": self.classification.value,
            "unavailable_reasons": list(self.unavailable_reasons),
        }


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Governed recommendation definition separated from mutable workflow facts."""

    recommendation_id: str
    source_system: str
    source_record_id: str
    source_classification: SourceClassification
    plant_id: str
    equipment_id: str
    recommendation_type: str
    action: str
    rationale: str
    priority_rank: int
    status: RecommendationStatus = RecommendationStatus.PROPOSED
    status_classification: SourceClassification = SourceClassification.CONFIGURED
    owner: RecommendationOwner = RecommendationOwner()
    evidence: tuple[EvidenceReference, ...] = ()

    def __post_init__(self) -> None:
        expected = stable_recommendation_id(self.source_system, self.source_record_id)
        if self.recommendation_id != expected:
            raise ValueError("recommendation_id must match stable source identity.")
        for name in (
            "plant_id",
            "equipment_id",
            "recommendation_type",
            "action",
            "rationale",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.priority_rank < 1:
            raise ValueError("priority_rank must be positive.")
        if self.status_classification not in {
            SourceClassification.CONFIGURED,
            SourceClassification.USER_ENTERED,
        }:
            raise ValueError(
                "Recommendation status must be CONFIGURED initialization or "
                "USER_ENTERED workflow state."
            )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_classification"] = self.source_classification.value
        payload["status"] = self.status.value
        payload["status_classification"] = self.status_classification.value
        payload["owner"]["classification"] = self.owner.classification.value
        for evidence in payload["evidence"]:
            evidence["evidence_type"] = evidence["evidence_type"].value
            evidence["relationship"] = evidence["relationship"].value
            evidence["classification"] = evidence["classification"].value
            if evidence["observed_at"] is not None:
                evidence["observed_at"] = evidence["observed_at"].isoformat()
        return payload


class GovernanceStore:
    """Non-durable in-memory boundary with append-only audit semantics."""

    def __init__(self, recommendations: tuple[Recommendation, ...]) -> None:
        self._recommendations = {
            item.recommendation_id: item for item in recommendations
        }
        if len(self._recommendations) != len(recommendations):
            raise ValueError("recommendation IDs must be unique.")
        self._events: list[AuditEvent] = []

    @property
    def durable(self) -> bool:
        return False

    def get(self, recommendation_id: str) -> Recommendation | None:
        return self._recommendations.get(recommendation_id)

    def history(self, recommendation_id: str) -> tuple[AuditEvent, ...]:
        return tuple(
            event
            for event in self._events
            if event.recommendation_id == recommendation_id
        )

    def transition(
        self,
        recommendation_id: str,
        new_status: RecommendationStatus,
        *,
        actor: GovernanceActor,
        occurred_at: datetime,
        note: str | None = None,
    ) -> Recommendation:
        self._authorize(actor)
        current = self._require(recommendation_id)
        if new_status == current.status:
            raise ValueError("Recommendation is already in the requested status.")
        if new_status not in ALLOWED_TRANSITIONS[current.status]:
            raise ValueError(
                "Invalid lifecycle transition: "
                f"{current.status.value} -> {new_status.value}."
            )
        self._validate_event_time(recommendation_id, occurred_at)
        updated = replace(
            current,
            status=new_status,
            status_classification=SourceClassification.USER_ENTERED,
        )
        self._recommendations[recommendation_id] = updated
        self._events.append(
            AuditEvent(
                recommendation_id,
                AuditEventType.STATUS_CHANGED,
                current.status.value,
                new_status.value,
                actor,
                occurred_at,
                note,
            )
        )
        return updated

    def assign_owner(
        self,
        recommendation_id: str,
        owner: RecommendationOwner,
        *,
        actor: GovernanceActor,
        occurred_at: datetime,
        note: str | None = None,
    ) -> Recommendation:
        self._authorize(actor)
        if owner.classification is not SourceClassification.USER_ENTERED:
            raise ValueError("Owner assignment must be USER_ENTERED.")
        current = self._require(recommendation_id)
        if owner == current.owner:
            raise ValueError("Recommendation already has the requested owner.")
        self._validate_event_time(recommendation_id, occurred_at)
        updated = replace(current, owner=owner)
        self._recommendations[recommendation_id] = updated
        self._events.append(
            AuditEvent(
                recommendation_id,
                AuditEventType.OWNER_ASSIGNED,
                current.owner.label,
                owner.label,
                actor,
                occurred_at,
                note,
            )
        )
        return updated

    def add_review_note(
        self,
        recommendation_id: str,
        note: str,
        *,
        actor: GovernanceActor,
        occurred_at: datetime,
    ) -> Recommendation:
        """Append a user-entered note without rewriting recommendation state."""
        self._authorize(actor)
        current = self._require(recommendation_id)
        normalized_note = _required(note, "note")
        self._validate_event_time(recommendation_id, occurred_at)
        self._events.append(
            AuditEvent(
                recommendation_id,
                AuditEventType.REVIEW_NOTE_ADDED,
                None,
                normalized_note,
                actor,
                occurred_at,
                normalized_note,
            )
        )
        return current

    def _require(self, recommendation_id: str) -> Recommendation:
        recommendation = self.get(recommendation_id)
        if recommendation is None:
            raise KeyError(f"Unknown recommendation: {recommendation_id}")
        return recommendation

    def _validate_event_time(
        self, recommendation_id: str, occurred_at: datetime
    ) -> None:
        normalized = _aware(occurred_at, "occurred_at")
        history = self.history(recommendation_id)
        if history and normalized < history[-1].occurred_at:
            raise ValueError("Audit events must be appended in chronological order.")

    @staticmethod
    def _authorize(actor: GovernanceActor) -> None:
        if actor.role not in {"operator", "admin"}:
            raise PermissionError("The actor is not authorized for governance writes.")


def calculate_energy_revenue_at_risk(
    energy_at_risk_mwh: Decimal,
    *,
    assumptions: FinancialAssumptions,
    energy_classification: SourceClassification,
) -> FinancialCalculation:
    """Calculate future production revenue exposure only with complete inputs."""
    if energy_at_risk_mwh < 0:
        raise ValueError("energy_at_risk_mwh must not be negative.")
    reasons: list[str] = []
    if assumptions.energy_sale_price_per_mwh is None:
        reasons.append("Approved energy-sale price is unavailable.")
    if assumptions.currency is None:
        reasons.append("Currency is unavailable.")
    if assumptions.analysis_horizon is None:
        reasons.append("Analysis horizon is unavailable.")
    if energy_classification is SourceClassification.UNAVAILABLE:
        reasons.append("Energy-at-risk provenance is unavailable.")
    inputs = {
        "energy_at_risk_mwh": str(energy_at_risk_mwh),
        "energy_classification": energy_classification.value,
        "energy_sale_price_per_mwh": (
            str(assumptions.energy_sale_price_per_mwh)
            if assumptions.energy_sale_price_per_mwh is not None
            else "UNAVAILABLE"
        ),
        "price_classification": assumptions.classification.value,
    }
    if reasons:
        return FinancialCalculation(
            "Revenue at Risk",
            None,
            assumptions.currency,
            "energy_at_risk_mwh * energy_sale_price_per_mwh",
            inputs,
            assumptions.assumption_version,
            assumptions.analysis_horizon,
            SourceClassification.UNAVAILABLE,
            tuple(reasons),
        )
    amount = energy_at_risk_mwh * assumptions.energy_sale_price_per_mwh  # type: ignore[operator]
    return FinancialCalculation(
        "Revenue at Risk",
        amount,
        assumptions.currency,
        "energy_at_risk_mwh * energy_sale_price_per_mwh",
        inputs,
        assumptions.assumption_version,
        assumptions.analysis_horizon,
        SourceClassification.DERIVED,
    )


def calculate_roi(
    *, benefit: Decimal | None, cost: Decimal | None, currency: str | None
) -> FinancialCalculation:
    """Calculate ROI only when benefit, non-zero cost, and currency exist."""
    reasons: list[str] = []
    if benefit is None:
        reasons.append("Benefit is unavailable.")
    if cost is None:
        reasons.append("Investment cost is unavailable.")
    elif cost <= 0:
        reasons.append("Investment cost must be greater than zero.")
    if currency is None:
        reasons.append("Currency is unavailable.")
    inputs = {
        "benefit": str(benefit) if benefit is not None else "UNAVAILABLE",
        "investment_cost": str(cost) if cost is not None else "UNAVAILABLE",
    }
    if reasons:
        return FinancialCalculation(
            "ROI",
            None,
            currency,
            "((benefit - investment_cost) / investment_cost) * 100",
            inputs,
            None,
            None,
            SourceClassification.UNAVAILABLE,
            tuple(reasons),
        )
    amount = ((benefit - cost) / cost) * Decimal("100")  # type: ignore[operator]
    return FinancialCalculation(
        "ROI",
        amount,
        currency,
        "((benefit - investment_cost) / investment_cost) * 100",
        inputs,
        None,
        None,
        SourceClassification.DERIVED,
    )
