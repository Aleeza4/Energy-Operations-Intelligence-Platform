"""
Unit tests for the EOIP Tariff SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from eoip.database.models.tariff import TariffORM
from eoip.synthetic.models.tariff import (
    Tariff,
    TariffStatus,
    TariffType,
)


def _domain_tariff(**overrides: object) -> Tariff:
    """Return a valid Tariff domain model with optional overrides."""
    data: dict[str, object] = {
        "tariff_id": "TAR-00001",
        "plant_id": "PLANT-001",
        "tariff_name": "Solar Plant PPA",
        "tariff_type": TariffType.POWER_PURCHASE_AGREEMENT,
        "currency_code": "PKR",
        "energy_rate_per_kwh": 28.5,
        "effective_from": date(2025, 1, 1),
        "effective_to": date(2030, 12, 31),
        "demand_rate_per_kw": 120.0,
        "escalation_rate_pct": 5.0,
        "status": TariffStatus.ACTIVE,
        "contract_reference": "PPA-2025-001",
        "notes": "Annual escalation applies.",
    }
    data.update(overrides)
    return Tariff(**data)


def _orm_tariff(**overrides: object) -> TariffORM:
    """Return a valid TariffORM object with optional overrides."""
    data: dict[str, object] = {
        "tariff_id": "TAR-00001",
        "plant_id": "PLANT-001",
        "tariff_name": "Solar Plant PPA",
        "tariff_type": TariffType.POWER_PURCHASE_AGREEMENT.value,
        "currency_code": "PKR",
        "energy_rate_per_kwh": 28.5,
        "effective_from": date(2025, 1, 1),
        "effective_to": date(2030, 12, 31),
        "demand_rate_per_kw": 120.0,
        "escalation_rate_pct": 5.0,
        "status": TariffStatus.ACTIVE.value,
        "contract_reference": "PPA-2025-001",
        "notes": "Annual escalation applies.",
    }
    data.update(overrides)
    return TariffORM(**data)


def test_table_name() -> None:
    """Verify the mapped database table name."""
    assert TariffORM.__tablename__ == "tariffs"


def test_primary_key_column() -> None:
    """Verify tariff_id is the only primary-key column."""
    primary_keys = {column.name for column in TariffORM.__table__.primary_key.columns}

    assert primary_keys == {"tariff_id"}


def test_expected_columns_exist() -> None:
    """Verify the complete persistence contract."""
    assert set(TariffORM.__table__.columns.keys()) == {
        "tariff_id",
        "plant_id",
        "tariff_name",
        "tariff_type",
        "currency_code",
        "energy_rate_per_kwh",
        "effective_from",
        "effective_to",
        "demand_rate_per_kw",
        "escalation_rate_pct",
        "status",
        "contract_reference",
        "notes",
        "inserted_at",
        "updated_at",
    }


def test_required_columns_are_not_nullable() -> None:
    """Verify required tariff fields are non-nullable."""
    for column_name in (
        "tariff_id",
        "plant_id",
        "tariff_name",
        "tariff_type",
        "currency_code",
        "energy_rate_per_kwh",
        "effective_from",
        "escalation_rate_pct",
        "status",
        "inserted_at",
        "updated_at",
    ):
        assert TariffORM.__table__.columns[column_name].nullable is False


def test_optional_columns_are_nullable() -> None:
    """Verify optional tariff fields remain nullable."""
    for column_name in (
        "effective_to",
        "demand_rate_per_kw",
        "contract_reference",
        "notes",
    ):
        assert TariffORM.__table__.columns[column_name].nullable is True


def test_plant_foreign_key_exists() -> None:
    """Verify the plant foreign-key target."""
    targets = {
        foreign_key.target_fullname for foreign_key in TariffORM.__table__.foreign_keys
    }

    assert targets == {"plants.plant_id"}


def test_plant_foreign_key_actions() -> None:
    """Verify plant foreign-key update and delete behavior."""
    foreign_key = next(iter(TariffORM.__table__.foreign_keys))

    assert foreign_key.parent.name == "plant_id"
    assert foreign_key.onupdate == "CASCADE"
    assert foreign_key.ondelete == "RESTRICT"


def test_foreign_key_constraint_is_declared() -> None:
    """Verify SQLAlchemy registers one foreign-key constraint."""
    constraints = [
        constraint
        for constraint in TariffORM.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(constraints) == 1


def test_expected_check_constraints_exist() -> None:
    """Verify controlled values, dates, and numeric constraints."""
    constraint_names = {
        constraint.name
        for constraint in TariffORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert constraint_names == {
        "ck_tariffs_valid_tariff_type",
        "ck_tariffs_valid_status",
        "ck_tariffs_energy_rate_non_negative",
        "ck_tariffs_demand_rate_non_negative",
        "ck_tariffs_escalation_rate_range",
        "ck_tariffs_effective_date_order",
        "ck_tariffs_expired_status_requires_end_date",
    }


def test_expected_indexes_exist() -> None:
    """Verify common tariff query indexes are declared."""
    index_names = {
        index.name for index in TariffORM.__table__.indexes if isinstance(index, Index)
    }

    assert index_names == {
        "ix_tariffs_plant_id",
        "ix_tariffs_tariff_type",
        "ix_tariffs_status",
        "ix_tariffs_effective_from",
        "ix_tariffs_effective_to",
        "ix_tariffs_plant_status",
        "ix_tariffs_plant_effective_from",
    }


@pytest.mark.parametrize(
    ("index_name", "expected_columns"),
    [
        ("ix_tariffs_plant_status", ("plant_id", "status")),
        (
            "ix_tariffs_plant_effective_from",
            ("plant_id", "effective_from"),
        ),
    ],
)
def test_composite_index_column_order(
    index_name: str,
    expected_columns: tuple[str, ...],
) -> None:
    """Verify composite tariff index column ordering."""
    index = next(
        item for item in TariffORM.__table__.indexes if item.name == index_name
    )

    assert tuple(column.name for column in index.columns) == expected_columns


def test_from_domain_maps_all_fields() -> None:
    """Verify conversion from the authoritative domain model."""
    tariff = _domain_tariff(
        plant_id="PLANT-002",
        tariff_name="Feed-in Tariff",
        tariff_type=TariffType.FEED_IN,
        currency_code="USD",
        energy_rate_per_kwh=0.12,
        effective_from=date(2024, 1, 1),
        effective_to=date(2029, 12, 31),
        demand_rate_per_kw=None,
        escalation_rate_pct=2.5,
        status=TariffStatus.ACTIVE,
        contract_reference="FIT-2024-01",
        notes=None,
    )

    orm = TariffORM.from_domain(tariff)

    assert orm.tariff_id == "TAR-00001"
    assert orm.plant_id == "PLANT-002"
    assert orm.tariff_name == "Feed-in Tariff"
    assert orm.tariff_type == TariffType.FEED_IN.value
    assert orm.currency_code == "USD"
    assert orm.energy_rate_per_kwh == 0.12
    assert orm.effective_from == date(2024, 1, 1)
    assert orm.effective_to == date(2029, 12, 31)
    assert orm.demand_rate_per_kw is None
    assert orm.escalation_rate_pct == 2.5
    assert orm.status == TariffStatus.ACTIVE.value
    assert orm.contract_reference == "FIT-2024-01"
    assert orm.notes is None


def test_from_domain_preserves_none_values() -> None:
    """Verify optional values remain None during conversion."""
    tariff = _domain_tariff(
        effective_to=None,
        demand_rate_per_kw=None,
        contract_reference=None,
        notes=None,
    )

    orm = TariffORM.from_domain(tariff)

    assert orm.effective_to is None
    assert orm.demand_rate_per_kw is None
    assert orm.contract_reference is None
    assert orm.notes is None


def test_from_domain_rejects_invalid_type() -> None:
    """Verify conversion rejects non-Tariff values."""
    with pytest.raises(TypeError, match="Tariff instance"):
        TariffORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    """Verify conversion back to the Tariff domain model."""
    orm = _orm_tariff(
        tariff_type=TariffType.MERCHANT.value,
        status=TariffStatus.EXPIRED.value,
    )

    tariff = orm.to_domain()

    assert isinstance(tariff, Tariff)
    assert tariff.tariff_id == orm.tariff_id
    assert tariff.plant_id == orm.plant_id
    assert tariff.tariff_name == orm.tariff_name
    assert tariff.tariff_type is TariffType.MERCHANT
    assert tariff.currency_code == orm.currency_code
    assert tariff.energy_rate_per_kwh == orm.energy_rate_per_kwh
    assert tariff.effective_from == orm.effective_from
    assert tariff.effective_to == orm.effective_to
    assert tariff.demand_rate_per_kw == orm.demand_rate_per_kw
    assert tariff.escalation_rate_pct == orm.escalation_rate_pct
    assert tariff.status is TariffStatus.EXPIRED
    assert tariff.contract_reference == orm.contract_reference
    assert tariff.notes == orm.notes


def test_domain_round_trip_preserves_values() -> None:
    """Verify domain-to-ORM-to-domain conversion is lossless."""
    original = _domain_tariff(
        tariff_type=TariffType.FIXED,
        demand_rate_per_kw=None,
    )

    restored = TariffORM.from_domain(original).to_domain()

    assert restored == original


def test_duration_days_for_bounded_tariff() -> None:
    """Verify inclusive tariff duration calculation."""
    orm = _orm_tariff(
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 1, 31),
    )

    assert orm.duration_days == 31


def test_duration_days_is_none_without_end_date() -> None:
    """Verify open-ended tariffs have no fixed duration."""
    assert _orm_tariff(effective_to=None).duration_days is None


def test_is_current_for_active_tariff() -> None:
    """Verify active tariff spanning today is current."""
    today = date.today()
    orm = _orm_tariff(
        effective_from=today - timedelta(days=30),
        effective_to=today + timedelta(days=30),
        status=TariffStatus.ACTIVE.value,
    )

    assert orm.is_current is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": TariffStatus.DRAFT.value},
        {"status": TariffStatus.EXPIRED.value},
        {"status": TariffStatus.CANCELLED.value},
        {"effective_from": date.today() + timedelta(days=1)},
        {"effective_to": date.today() - timedelta(days=1)},
    ],
)
def test_is_current_false_when_not_current(
    overrides: dict[str, object],
) -> None:
    """Verify non-current lifecycle and date combinations."""
    orm = _orm_tariff(**overrides)

    assert orm.is_current is False


@pytest.mark.parametrize(
    ("energy_kwh", "rate", "expected"),
    [
        (1_000.0, 28.5, 28_500.0),
        (250.5, 0.12, 30.06),
        (0.0, 28.5, 0.0),
    ],
)
def test_calculate_energy_revenue(
    energy_kwh: float,
    rate: float,
    expected: float,
) -> None:
    """Verify energy revenue calculation."""
    orm = _orm_tariff(energy_rate_per_kwh=rate)

    assert orm.calculate_energy_revenue(energy_kwh) == expected


@pytest.mark.parametrize(
    ("demand_kw", "rate", "expected"),
    [
        (500.0, 120.0, 60_000.0),
        (12.5, 2.25, 28.12),
        (0.0, 120.0, 0.0),
    ],
)
def test_calculate_demand_charge(
    demand_kw: float,
    rate: float,
    expected: float,
) -> None:
    """Verify demand-charge calculation."""
    orm = _orm_tariff(demand_rate_per_kw=rate)

    assert orm.calculate_demand_charge(demand_kw) == expected


def test_calculate_demand_charge_is_zero_without_rate() -> None:
    """Verify absent demand rate produces no charge."""
    orm = _orm_tariff(demand_rate_per_kw=None)

    assert orm.calculate_demand_charge(500.0) == 0.0


def test_calculate_total_value() -> None:
    """Verify combined energy and demand tariff value."""
    orm = _orm_tariff(
        energy_rate_per_kwh=10.0,
        demand_rate_per_kw=5.0,
    )

    assert (
        orm.calculate_total_value(
            energy_kwh=100.0,
            demand_kw=20.0,
        )
        == 1_100.0
    )


@pytest.mark.parametrize(
    ("method_name", "value"),
    [
        ("calculate_energy_revenue", -1.0),
        ("calculate_energy_revenue", float("nan")),
        ("calculate_energy_revenue", float("inf")),
        ("calculate_demand_charge", -1.0),
        ("calculate_demand_charge", float("nan")),
        ("calculate_demand_charge", float("inf")),
    ],
)
def test_runtime_calculations_reject_invalid_numeric_values(
    method_name: str,
    value: float,
) -> None:
    """Verify runtime calculations reject invalid numeric inputs."""
    orm = _orm_tariff()
    method = getattr(orm, method_name)

    with pytest.raises(ValueError):
        method(value)


@pytest.mark.parametrize(
    ("method_name", "value"),
    [
        ("calculate_energy_revenue", True),
        ("calculate_energy_revenue", "100"),
        ("calculate_demand_charge", False),
        ("calculate_demand_charge", "20"),
    ],
)
def test_runtime_calculations_reject_invalid_types(
    method_name: str,
    value: object,
) -> None:
    """Verify runtime calculations reject non-numeric inputs."""
    orm = _orm_tariff()
    method = getattr(orm, method_name)

    with pytest.raises(TypeError):
        method(value)  # type: ignore[arg-type]


def test_update_from_domain_updates_mutable_fields() -> None:
    """Verify ORM values can be refreshed from a matching domain object."""
    orm = _orm_tariff()
    updated = _domain_tariff(
        plant_id="PLANT-002",
        tariff_name="Updated Merchant Tariff",
        tariff_type=TariffType.MERCHANT,
        currency_code="EUR",
        energy_rate_per_kwh=0.09,
        effective_from=date(2026, 1, 1),
        effective_to=date(2028, 12, 31),
        demand_rate_per_kw=15.0,
        escalation_rate_pct=3.5,
        status=TariffStatus.DRAFT,
        contract_reference="MKT-2026-01",
        notes="Subject to market review.",
    )

    orm.update_from_domain(updated)

    assert orm.plant_id == "PLANT-002"
    assert orm.tariff_name == "Updated Merchant Tariff"
    assert orm.tariff_type == TariffType.MERCHANT.value
    assert orm.currency_code == "EUR"
    assert orm.energy_rate_per_kwh == 0.09
    assert orm.effective_from == date(2026, 1, 1)
    assert orm.effective_to == date(2028, 12, 31)
    assert orm.demand_rate_per_kw == 15.0
    assert orm.escalation_rate_pct == 3.5
    assert orm.status == TariffStatus.DRAFT.value
    assert orm.contract_reference == "MKT-2026-01"
    assert orm.notes == "Subject to market review."


def test_update_from_domain_rejects_invalid_type() -> None:
    """Verify update rejects non-Tariff values."""
    orm = _orm_tariff()

    with pytest.raises(TypeError, match="Tariff instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


def test_update_from_domain_rejects_different_identifier() -> None:
    """Verify persisted tariff identity cannot be changed."""
    orm = _orm_tariff()
    different = _domain_tariff(tariff_id="TAR-00002")

    with pytest.raises(ValueError, match="different tariff_id"):
        orm.update_from_domain(different)


def test_to_record_serializes_all_values() -> None:
    """Verify tariff records are serialization-ready."""
    inserted_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    updated_at = inserted_at + timedelta(hours=1)
    orm = _orm_tariff()
    orm.inserted_at = inserted_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "tariff_id": "TAR-00001",
        "plant_id": "PLANT-001",
        "tariff_name": "Solar Plant PPA",
        "tariff_type": TariffType.POWER_PURCHASE_AGREEMENT.value,
        "currency_code": "PKR",
        "energy_rate_per_kwh": 28.5,
        "effective_from": "2025-01-01",
        "effective_to": "2030-12-31",
        "demand_rate_per_kw": 120.0,
        "escalation_rate_pct": 5.0,
        "status": TariffStatus.ACTIVE.value,
        "contract_reference": "PPA-2025-001",
        "notes": "Annual escalation applies.",
        "is_current": orm.is_current,
        "duration_days": 2191,
        "inserted_at": inserted_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_to_record_handles_optional_values() -> None:
    """Verify optional tariff values serialize correctly."""
    record = _orm_tariff(
        effective_to=None,
        demand_rate_per_kw=None,
        contract_reference=None,
        notes=None,
    ).to_record()

    assert record["effective_to"] is None
    assert record["demand_rate_per_kw"] is None
    assert record["contract_reference"] is None
    assert record["notes"] is None
    assert record["duration_days"] is None


def test_to_record_handles_unset_audit_timestamps() -> None:
    """Verify unsaved ORM objects serialize missing audit timestamps."""
    record = _orm_tariff().to_record()

    assert record["inserted_at"] is None
    assert record["updated_at"] is None


def test_repr_contains_key_identity_fields() -> None:
    """Verify developer representation is concise and useful."""
    value = repr(_orm_tariff())

    assert "TariffORM" in value
    assert "TAR-00001" in value
    assert "PLANT-001" in value
    assert TariffType.POWER_PURCHASE_AGREEMENT.value in value
    assert TariffStatus.ACTIVE.value in value


def test_escalation_default_is_zero() -> None:
    """Verify escalation defaults to zero."""
    column = TariffORM.__table__.columns["escalation_rate_pct"]

    assert column.default is not None
    assert column.default.arg == 0.0
    assert column.server_default is not None


def test_status_default_matches_domain_default() -> None:
    """Verify ORM status defaults to active."""
    column = TariffORM.__table__.columns["status"]

    assert column.default is not None
    assert column.default.arg == TariffStatus.ACTIVE.value
    assert column.server_default is not None


def test_audit_columns_are_timezone_aware() -> None:
    """Verify audit timestamps preserve timezone data."""
    for column_name in ("inserted_at", "updated_at"):
        assert TariffORM.__table__.columns[column_name].type.timezone is True


def test_plant_relationship_configuration() -> None:
    """Verify tariffs link to PlantORM."""
    relationship_property = TariffORM.__mapper__.relationships["plant"]

    assert relationship_property.mapper.class_.__name__ == "PlantORM"
    assert relationship_property.uselist is False


def test_text_column_lengths_match_domain_contract() -> None:
    """Verify tariff text fields match domain maximum lengths."""
    assert TariffORM.__table__.columns["tariff_name"].type.length == 150
    assert TariffORM.__table__.columns["currency_code"].type.length == 3
    assert TariffORM.__table__.columns["contract_reference"].type.length == 100
    assert TariffORM.__table__.columns["notes"].type.length == 1_000


def test_numeric_columns_use_float_type() -> None:
    """Verify tariff numeric fields use floating-point storage."""
    for column_name in (
        "energy_rate_per_kwh",
        "demand_rate_per_kw",
        "escalation_rate_pct",
    ):
        assert TariffORM.__table__.columns[column_name].type.python_type is float
