"""
Unit tests for the EOIP Budget SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from eoip.database.models.budget import BudgetORM
from eoip.synthetic.models.budget import Budget, BudgetCategory, BudgetStatus


def _domain_budget(**overrides: object) -> Budget:
    """Return a valid Budget domain model with optional overrides."""
    data: dict[str, object] = {
        "budget_id": "BUD-00001",
        "plant_id": "PLANT-001",
        "budget_name": "Annual Maintenance Budget",
        "category": BudgetCategory.MAINTENANCE,
        "fiscal_year": 2026,
        "allocated_amount": 1_000_000.0,
        "spent_amount": 250_000.0,
        "currency_code": "PKR",
        "approved_on": date(2026, 1, 15),
        "status": BudgetStatus.APPROVED,
    }
    data.update(overrides)
    return Budget(**data)


def _orm_budget(**overrides: object) -> BudgetORM:
    """Return a valid BudgetORM object with optional overrides."""
    data: dict[str, object] = {
        "budget_id": "BUD-00001",
        "plant_id": "PLANT-001",
        "budget_name": "Annual Maintenance Budget",
        "category": BudgetCategory.MAINTENANCE.value,
        "fiscal_year": 2026,
        "allocated_amount": 1_000_000.0,
        "spent_amount": 250_000.0,
        "currency_code": "PKR",
        "approved_on": date(2026, 1, 15),
        "status": BudgetStatus.APPROVED.value,
    }
    data.update(overrides)
    return BudgetORM(**data)


def test_table_name() -> None:
    assert BudgetORM.__tablename__ == "budgets"


def test_primary_key_column() -> None:
    primary_keys = {column.name for column in BudgetORM.__table__.primary_key.columns}
    assert primary_keys == {"budget_id"}


def test_expected_columns_exist() -> None:
    assert set(BudgetORM.__table__.columns.keys()) == {
        "budget_id",
        "plant_id",
        "budget_name",
        "category",
        "fiscal_year",
        "allocated_amount",
        "spent_amount",
        "currency_code",
        "approved_on",
        "status",
        "inserted_at",
        "updated_at",
    }


def test_required_columns_are_not_nullable() -> None:
    for column_name in (
        "budget_id",
        "plant_id",
        "budget_name",
        "category",
        "fiscal_year",
        "allocated_amount",
        "spent_amount",
        "currency_code",
        "status",
        "inserted_at",
        "updated_at",
    ):
        assert BudgetORM.__table__.columns[column_name].nullable is False


def test_approved_on_is_nullable() -> None:
    assert BudgetORM.__table__.columns["approved_on"].nullable is True


def test_plant_foreign_key_exists() -> None:
    targets = {
        foreign_key.target_fullname for foreign_key in BudgetORM.__table__.foreign_keys
    }
    assert targets == {"plants.plant_id"}


def test_plant_foreign_key_actions() -> None:
    foreign_key = next(iter(BudgetORM.__table__.foreign_keys))
    assert foreign_key.parent.name == "plant_id"
    assert foreign_key.onupdate == "CASCADE"
    assert foreign_key.ondelete == "RESTRICT"


def test_foreign_key_constraint_is_declared() -> None:
    constraints = [
        constraint
        for constraint in BudgetORM.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert len(constraints) == 1


def test_expected_check_constraints_exist() -> None:
    constraint_names = {
        constraint.name
        for constraint in BudgetORM.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert constraint_names == {
        "ck_budgets_valid_category",
        "ck_budgets_valid_status",
        "ck_budgets_fiscal_year_range",
        "ck_budgets_allocated_amount_non_negative",
        "ck_budgets_spent_amount_non_negative",
        "ck_budgets_spent_not_above_allocated",
        "ck_budgets_approved_status_requires_date",
    }


def test_expected_indexes_exist() -> None:
    index_names = {
        index.name for index in BudgetORM.__table__.indexes if isinstance(index, Index)
    }
    assert index_names == {
        "ix_budgets_plant_id",
        "ix_budgets_category",
        "ix_budgets_status",
        "ix_budgets_fiscal_year",
        "ix_budgets_approved_on",
        "ix_budgets_plant_fiscal_year",
    }


def test_composite_index_column_order() -> None:
    index = next(
        item
        for item in BudgetORM.__table__.indexes
        if item.name == "ix_budgets_plant_fiscal_year"
    )
    assert tuple(column.name for column in index.columns) == (
        "plant_id",
        "fiscal_year",
    )


def test_from_domain_maps_all_fields() -> None:
    budget = _domain_budget(
        plant_id="PLANT-002",
        budget_name="Plant Expansion CAPEX",
        category=BudgetCategory.CAPEX,
        fiscal_year=2027,
        allocated_amount=2_500_000.0,
        spent_amount=500_000.0,
        currency_code="USD",
        approved_on=date(2027, 2, 1),
        status=BudgetStatus.APPROVED,
    )
    orm = BudgetORM.from_domain(budget)

    assert orm.budget_id == "BUD-00001"
    assert orm.plant_id == "PLANT-002"
    assert orm.budget_name == "Plant Expansion CAPEX"
    assert orm.category == BudgetCategory.CAPEX.value
    assert orm.fiscal_year == 2027
    assert orm.allocated_amount == 2_500_000.0
    assert orm.spent_amount == 500_000.0
    assert orm.currency_code == "USD"
    assert orm.approved_on == date(2027, 2, 1)
    assert orm.status == BudgetStatus.APPROVED.value


def test_from_domain_preserves_none_approval_date() -> None:
    budget = _domain_budget(approved_on=None, status=BudgetStatus.DRAFT)
    orm = BudgetORM.from_domain(budget)

    assert orm.approved_on is None
    assert orm.status == BudgetStatus.DRAFT.value


def test_from_domain_rejects_invalid_type() -> None:
    with pytest.raises(TypeError, match="Budget instance"):
        BudgetORM.from_domain(object())  # type: ignore[arg-type]


def test_to_domain_returns_authoritative_model() -> None:
    orm = _orm_budget(
        category=BudgetCategory.OPEX.value,
        status=BudgetStatus.CLOSED.value,
    )
    budget = orm.to_domain()

    assert isinstance(budget, Budget)
    assert budget.budget_id == orm.budget_id
    assert budget.plant_id == orm.plant_id
    assert budget.budget_name == orm.budget_name
    assert budget.category is BudgetCategory.OPEX
    assert budget.fiscal_year == orm.fiscal_year
    assert budget.allocated_amount == orm.allocated_amount
    assert budget.spent_amount == orm.spent_amount
    assert budget.currency_code == orm.currency_code
    assert budget.approved_on == orm.approved_on
    assert budget.status is BudgetStatus.CLOSED


def test_domain_round_trip_preserves_values() -> None:
    original = _domain_budget(category=BudgetCategory.OPERATIONS)
    restored = BudgetORM.from_domain(original).to_domain()
    assert restored == original


@pytest.mark.parametrize(
    ("allocated_amount", "spent_amount", "expected"),
    [
        (1_000.0, 250.0, 750.0),
        (1_000.0, 1_000.0, 0.0),
        (1_000.005, 250.004, 750.0),
    ],
)
def test_remaining_amount(
    allocated_amount: float,
    spent_amount: float,
    expected: float,
) -> None:
    orm = _orm_budget(
        allocated_amount=allocated_amount,
        spent_amount=spent_amount,
    )
    assert orm.remaining_amount == expected


@pytest.mark.parametrize(
    ("allocated_amount", "spent_amount", "expected"),
    [
        (1_000.0, 250.0, 25.0),
        (1_000.0, 1_000.0, 100.0),
        (800.0, 333.0, 41.62),
        (0.0, 0.0, 0.0),
    ],
)
def test_utilization_pct(
    allocated_amount: float,
    spent_amount: float,
    expected: float,
) -> None:
    orm = _orm_budget(
        allocated_amount=allocated_amount,
        spent_amount=spent_amount,
    )
    assert orm.utilization_pct == expected


@pytest.mark.parametrize(
    ("allocated_amount", "spent_amount", "expected"),
    [
        (1_000.0, 900.0, False),
        (1_000.0, 1_000.0, False),
        (1_000.0, 1_100.0, True),
    ],
)
def test_is_over_budget(
    allocated_amount: float,
    spent_amount: float,
    expected: bool,
) -> None:
    orm = _orm_budget(
        allocated_amount=allocated_amount,
        spent_amount=spent_amount,
    )
    assert orm.is_over_budget is expected


def test_update_from_domain_updates_mutable_fields() -> None:
    orm = _orm_budget()
    updated = _domain_budget(
        plant_id="PLANT-002",
        budget_name="Updated Operations Budget",
        category=BudgetCategory.OPERATIONS,
        fiscal_year=2028,
        allocated_amount=3_000_000.0,
        spent_amount=750_000.0,
        currency_code="EUR",
        approved_on=date(2028, 1, 20),
        status=BudgetStatus.APPROVED,
    )
    orm.update_from_domain(updated)

    assert orm.plant_id == "PLANT-002"
    assert orm.budget_name == "Updated Operations Budget"
    assert orm.category == BudgetCategory.OPERATIONS.value
    assert orm.fiscal_year == 2028
    assert orm.allocated_amount == 3_000_000.0
    assert orm.spent_amount == 750_000.0
    assert orm.currency_code == "EUR"
    assert orm.approved_on == date(2028, 1, 20)
    assert orm.status == BudgetStatus.APPROVED.value


def test_update_from_domain_rejects_invalid_type() -> None:
    orm = _orm_budget()
    with pytest.raises(TypeError, match="Budget instance"):
        orm.update_from_domain(object())  # type: ignore[arg-type]


def test_update_from_domain_rejects_different_identifier() -> None:
    orm = _orm_budget()
    different = _domain_budget(budget_id="BUD-00002")

    with pytest.raises(ValueError, match="different budget_id"):
        orm.update_from_domain(different)


def test_to_record_serializes_all_values() -> None:
    inserted_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    updated_at = inserted_at + timedelta(hours=1)
    orm = _orm_budget()
    orm.inserted_at = inserted_at
    orm.updated_at = updated_at

    record = orm.to_record()

    assert record == {
        "budget_id": "BUD-00001",
        "plant_id": "PLANT-001",
        "budget_name": "Annual Maintenance Budget",
        "category": BudgetCategory.MAINTENANCE.value,
        "fiscal_year": 2026,
        "allocated_amount": 1_000_000.0,
        "spent_amount": 250_000.0,
        "currency_code": "PKR",
        "approved_on": "2026-01-15",
        "status": BudgetStatus.APPROVED.value,
        "remaining_amount": 750_000.0,
        "utilization_pct": 25.0,
        "is_over_budget": False,
        "inserted_at": inserted_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_to_record_handles_missing_approval_date() -> None:
    record = _orm_budget(
        approved_on=None,
        status=BudgetStatus.DRAFT.value,
    ).to_record()

    assert record["approved_on"] is None
    assert record["status"] == BudgetStatus.DRAFT.value


def test_to_record_handles_unset_audit_timestamps() -> None:
    record = _orm_budget().to_record()
    assert record["inserted_at"] is None
    assert record["updated_at"] is None


def test_repr_contains_key_identity_fields() -> None:
    value = repr(_orm_budget())

    assert "BudgetORM" in value
    assert "BUD-00001" in value
    assert "PLANT-001" in value
    assert "2026" in value
    assert BudgetStatus.APPROVED.value in value


def test_spent_amount_default_is_zero() -> None:
    column = BudgetORM.__table__.columns["spent_amount"]

    assert column.default is not None
    assert column.default.arg == 0.0
    assert column.server_default is not None


def test_currency_code_default_is_pkr() -> None:
    column = BudgetORM.__table__.columns["currency_code"]

    assert column.default is not None
    assert column.default.arg == "PKR"
    assert column.server_default is not None


def test_status_default_matches_domain_default() -> None:
    column = BudgetORM.__table__.columns["status"]

    assert column.default is not None
    assert column.default.arg == BudgetStatus.DRAFT.value
    assert column.server_default is not None


def test_audit_columns_are_timezone_aware() -> None:
    for column_name in ("inserted_at", "updated_at"):
        assert BudgetORM.__table__.columns[column_name].type.timezone is True


def test_plant_relationship_configuration() -> None:
    relationship_property = BudgetORM.__mapper__.relationships["plant"]

    assert relationship_property.mapper.class_.__name__ == "PlantORM"
    assert relationship_property.uselist is False


def test_budget_name_length_is_150() -> None:
    assert BudgetORM.__table__.columns["budget_name"].type.length == 150


def test_currency_code_length_is_three() -> None:
    assert BudgetORM.__table__.columns["currency_code"].type.length == 3


def test_amount_columns_use_float_type() -> None:
    for column_name in ("allocated_amount", "spent_amount"):
        assert BudgetORM.__table__.columns[column_name].type.python_type is float


def test_fiscal_year_uses_integer_type() -> None:
    assert BudgetORM.__table__.columns["fiscal_year"].type.python_type is int
