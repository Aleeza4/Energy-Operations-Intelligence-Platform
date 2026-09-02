"""Phase M recommendation-governance and financial-traceability tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from eoip.governance import (
    EvidenceReference,
    EvidenceRelationship,
    EvidenceType,
    FinancialAssumptions,
    GovernanceActor,
    GovernanceStore,
    Recommendation,
    RecommendationOwner,
    RecommendationStatus,
    SourceClassification,
    calculate_energy_revenue_at_risk,
    calculate_roi,
    stable_recommendation_id,
)


def _recommendation() -> Recommendation:
    source = "optimization-demo"
    record = "DEMO-001"
    return Recommendation(
        recommendation_id=stable_recommendation_id(source, record),
        source_system=source,
        source_record_id=record,
        source_classification=SourceClassification.REPRESENTATIVE_SYNTHETIC,
        plant_id="Solar Plant D",
        equipment_id="INV-005",
        recommendation_type="maintenance",
        action="Review asset condition.",
        rationale="Representative demonstration recommendation.",
        priority_rank=1,
    )


def _actor(role: str = "operator") -> GovernanceActor:
    return GovernanceActor(
        actor_id=f"test-{role}",
        role=role,
        classification=SourceClassification.USER_ENTERED,
    )


def test_stable_id_is_deterministic_export_safe_and_not_row_based() -> None:
    first = stable_recommendation_id("optimization-demo", "DEMO-001")
    assert first == stable_recommendation_id("optimization-demo", "DEMO-001")
    assert first.startswith("REC-")
    assert first != stable_recommendation_id("optimization-demo", "DEMO-002")


def test_demo_recommendation_initializes_proposed_and_unassigned() -> None:
    item = _recommendation()
    assert item.status is RecommendationStatus.PROPOSED
    assert item.owner.label == "Unassigned"
    assert item.owner.classification is SourceClassification.UNAVAILABLE


def test_valid_lifecycle_appends_ordered_immutable_history() -> None:
    item = _recommendation()
    store = GovernanceStore((item,))
    started = datetime(2026, 8, 27, tzinfo=UTC)
    store.transition(
        item.recommendation_id,
        RecommendationStatus.UNDER_REVIEW,
        actor=_actor(),
        occurred_at=started,
    )
    store.transition(
        item.recommendation_id,
        RecommendationStatus.APPROVED,
        actor=_actor(),
        occurred_at=started + timedelta(minutes=1),
    )
    history = store.history(item.recommendation_id)
    assert [event.new_value for event in history] == ["UNDER_REVIEW", "APPROVED"]
    assert store.get(item.recommendation_id).status_classification is (
        SourceClassification.USER_ENTERED
    )
    with pytest.raises(FrozenInstanceError):
        history[0].new_value = "REWRITTEN"  # type: ignore[misc]


def test_invalid_and_duplicate_transitions_are_rejected() -> None:
    item = _recommendation()
    store = GovernanceStore((item,))
    now = datetime(2026, 8, 27, tzinfo=UTC)
    with pytest.raises(ValueError, match="Invalid lifecycle"):
        store.transition(
            item.recommendation_id,
            RecommendationStatus.COMPLETED,
            actor=_actor(),
            occurred_at=now,
        )
    with pytest.raises(ValueError, match="already"):
        store.transition(
            item.recommendation_id,
            RecommendationStatus.PROPOSED,
            actor=_actor(),
            occurred_at=now,
        )


def test_viewer_cannot_assign_or_transition() -> None:
    item = _recommendation()
    store = GovernanceStore((item,))
    now = datetime(2026, 8, 27, tzinfo=UTC)
    with pytest.raises(PermissionError):
        store.transition(
            item.recommendation_id,
            RecommendationStatus.UNDER_REVIEW,
            actor=_actor("viewer"),
            occurred_at=now,
        )


def test_owner_assignment_is_explicit_user_input() -> None:
    item = _recommendation()
    store = GovernanceStore((item,))
    owner = RecommendationOwner(
        owner_id="role:maintenance",
        display_name="Maintenance",
        role="maintenance",
        classification=SourceClassification.USER_ENTERED,
    )
    updated = store.assign_owner(
        item.recommendation_id,
        owner,
        actor=_actor(),
        occurred_at=datetime(2026, 8, 27, tzinfo=UTC),
    )
    assert updated.owner.label == "Maintenance"
    assert store.durable is False


def test_duplicate_assignment_and_backdated_audit_event_are_rejected() -> None:
    item = _recommendation()
    store = GovernanceStore((item,))
    owner = RecommendationOwner(
        owner_id="role:maintenance",
        display_name="Maintenance",
        role="maintenance",
        classification=SourceClassification.USER_ENTERED,
    )
    now = datetime(2026, 8, 27, 12, tzinfo=UTC)
    store.assign_owner(item.recommendation_id, owner, actor=_actor(), occurred_at=now)
    with pytest.raises(ValueError, match="already has"):
        store.assign_owner(
            item.recommendation_id, owner, actor=_actor(), occurred_at=now
        )
    with pytest.raises(ValueError, match="chronological"):
        store.transition(
            item.recommendation_id,
            RecommendationStatus.UNDER_REVIEW,
            actor=_actor(),
            occurred_at=now - timedelta(seconds=1),
        )


def test_review_note_is_user_entered_append_only_audit_data() -> None:
    item = _recommendation()
    store = GovernanceStore((item,))
    store.add_review_note(
        item.recommendation_id,
        "Needs engineering review.",
        actor=_actor(),
        occurred_at=datetime(2026, 8, 27, tzinfo=UTC),
    )
    event = store.history(item.recommendation_id)[0]
    assert event.event_type.value == "REVIEW_NOTE_ADDED"
    assert event.new_value == "Needs engineering review."


def test_related_evidence_never_upgrades_to_causality() -> None:
    evidence = EvidenceReference(
        EvidenceType.ANOMALY,
        "demo-ui",
        "ANM-2031",
        EvidenceRelationship.RELATED_TO,
        SourceClassification.REPRESENTATIVE_SYNTHETIC,
        plant_id="Solar Plant D",
        equipment_id="INV-005",
    )
    assert evidence.relationship is EvidenceRelationship.RELATED_TO
    assert evidence.relationship is not EvidenceRelationship.CAUSED_BY


def test_missing_financial_inputs_make_revenue_at_risk_unavailable() -> None:
    assumptions = FinancialAssumptions("UNAVAILABLE-v1")
    result = calculate_energy_revenue_at_risk(
        Decimal("12.5"),
        assumptions=assumptions,
        energy_classification=SourceClassification.DERIVED,
    )
    assert result.amount is None
    assert result.classification is SourceClassification.UNAVAILABLE
    assert len(result.unavailable_reasons) == 3


def test_unknown_energy_provenance_prevents_monetary_conversion() -> None:
    assumptions = FinancialAssumptions(
        "TEST-v1",
        currency="USD",
        energy_sale_price_per_mwh=Decimal("50"),
        analysis_horizon="24 hours",
        classification=SourceClassification.REPRESENTATIVE_SYNTHETIC,
    )
    result = calculate_energy_revenue_at_risk(
        Decimal("2"),
        assumptions=assumptions,
        energy_classification=SourceClassification.UNAVAILABLE,
    )
    assert result.amount is None
    assert result.unavailable_reasons == ("Energy-at-risk provenance is unavailable.",)


def test_revenue_at_risk_preserves_formula_version_currency_and_horizon() -> None:
    assumptions = FinancialAssumptions(
        "TEST-v3",
        currency="usd",
        energy_sale_price_per_mwh=Decimal("50.25"),
        analysis_horizon="next 24 hours",
        classification=SourceClassification.REPRESENTATIVE_SYNTHETIC,
    )
    result = calculate_energy_revenue_at_risk(
        Decimal("2.00"),
        assumptions=assumptions,
        energy_classification=SourceClassification.REPRESENTATIVE_SYNTHETIC,
    )
    assert result.amount == Decimal("100.5000")
    assert result.currency == "USD"
    assert result.assumption_version == "TEST-v3"
    assert result.analysis_horizon == "next 24 hours"
    assert result.classification is SourceClassification.DERIVED


def test_zero_energy_is_valid_but_negative_energy_is_not() -> None:
    assumptions = FinancialAssumptions(
        "TEST-v1",
        currency="USD",
        energy_sale_price_per_mwh=Decimal("50"),
        analysis_horizon="24 hours",
        classification=SourceClassification.REPRESENTATIVE_SYNTHETIC,
    )
    assert calculate_energy_revenue_at_risk(
        Decimal("0"),
        assumptions=assumptions,
        energy_classification=SourceClassification.DERIVED,
    ).amount == Decimal("0")
    with pytest.raises(ValueError, match="must not be negative"):
        calculate_energy_revenue_at_risk(
            Decimal("-1"),
            assumptions=assumptions,
            energy_classification=SourceClassification.DERIVED,
        )


def test_roi_requires_benefit_cost_and_currency_without_defaults() -> None:
    unavailable = calculate_roi(benefit=None, cost=None, currency=None)
    assert unavailable.amount is None
    valid = calculate_roi(benefit=Decimal("150"), cost=Decimal("100"), currency="USD")
    assert valid.amount == Decimal("50.0")


def test_serialization_keeps_provenance_and_unavailable_owner() -> None:
    payload = _recommendation().to_dict()
    assert payload["recommendation_id"].startswith("REC-")
    assert payload["source_classification"] == "REPRESENTATIVE_SYNTHETIC"
    assert payload["owner"]["classification"] == "UNAVAILABLE"
    assert payload["status_classification"] == "CONFIGURED"


def test_financial_serialization_preserves_traceability_mapping() -> None:
    assumptions = FinancialAssumptions(
        "TEST-v4",
        currency="USD",
        energy_sale_price_per_mwh=Decimal("50.25"),
        analysis_horizon="next 24 hours",
        classification=SourceClassification.REPRESENTATIVE_SYNTHETIC,
    )
    payload = calculate_energy_revenue_at_risk(
        Decimal("2"),
        assumptions=assumptions,
        energy_classification=SourceClassification.REPRESENTATIVE_SYNTHETIC,
    ).to_dict()
    assert payload["amount"] == "100.50"
    assert payload["inputs"]["energy_classification"] == "REPRESENTATIVE_SYNTHETIC"
    assert payload["assumption_version"] == "TEST-v4"
