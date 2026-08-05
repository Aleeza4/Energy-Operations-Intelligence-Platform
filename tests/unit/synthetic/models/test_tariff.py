"""
Unit tests for the EOIP tariff domain model.

These tests verify tariff construction, normalization, validation, lifecycle
rules, revenue calculations, serialization, derived properties, and
dataclass immutability.
"""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from typing import Any

import pytest

from eoip.synthetic.models.tariff import (
    Tariff,
    TariffStatus,
    TariffType,
)


def _make_tariff(**overrides: Any) -> Tariff:
    """Create a valid active tariff with optional field overrides."""
    today = date.today()
    tariff_data: dict[str, Any] = {
        "tariff_id": "TAR-00001",
        "plant_id": "PLANT-001",
        "tariff_name": "Solar PPA",
        "tariff_type": TariffType.POWER_PURCHASE_AGREEMENT,
        "currency_code": "PKR",
        "energy_rate_per_kwh": 25.5,
        "effective_from": today - timedelta(days=30),
        "effective_to": today + timedelta(days=335),
        "demand_rate_per_kw": 2.0,
        "escalation_rate_pct": 5.0,
        "status": TariffStatus.ACTIVE,
        "contract_reference": "PPA-001",
        "notes": "Standard utility-scale solar tariff.",
    }
    tariff_data.update(overrides)
    return Tariff(**tariff_data)


def test_tariff_preserves_valid_fields() -> None:
    """A valid tariff should retain all supplied values."""
    tariff = _make_tariff()

    assert tariff.tariff_id == "TAR-00001"
    assert tariff.plant_id == "PLANT-001"
    assert tariff.tariff_name == "Solar PPA"
    assert tariff.tariff_type is TariffType.POWER_PURCHASE_AGREEMENT
    assert tariff.currency_code == "PKR"
    assert tariff.energy_rate_per_kwh == 25.5
    assert tariff.demand_rate_per_kw == 2.0
    assert tariff.escalation_rate_pct == 5.0
    assert tariff.status is TariffStatus.ACTIVE
    assert tariff.contract_reference == "PPA-001"
    assert tariff.notes == "Standard utility-scale solar tariff."


def test_tariff_normalizes_identifiers_and_text() -> None:
    """Identifiers and supported text fields should be normalized."""
    tariff = _make_tariff(
        tariff_id=" tar-00001 ",
        plant_id=" plant-001 ",
        tariff_name=" Solar PPA ",
        currency_code=" pkr ",
        contract_reference=" ppa-001 ",
        notes=" Standard utility-scale solar tariff. ",
    )

    assert tariff.tariff_id == "TAR-00001"
    assert tariff.plant_id == "PLANT-001"
    assert tariff.tariff_name == "Solar PPA"
    assert tariff.currency_code == "PKR"
    assert tariff.contract_reference == "PPA-001"
    assert tariff.notes == "Standard utility-scale solar tariff."


def test_tariff_uses_expected_defaults() -> None:
    """Optional fields should use documented defaults."""
    tariff = Tariff(
        tariff_id="TAR-00001",
        plant_id="PLANT-001",
        tariff_name="Fixed Export Tariff",
        tariff_type=TariffType.FIXED,
        currency_code="USD",
        energy_rate_per_kwh=0.08,
        effective_from=date.today(),
    )

    assert tariff.effective_to is None
    assert tariff.demand_rate_per_kw is None
    assert tariff.escalation_rate_pct == 0.0
    assert tariff.status is TariffStatus.ACTIVE
    assert tariff.contract_reference is None
    assert tariff.notes is None


@pytest.mark.parametrize("tariff_type", list(TariffType))
def test_tariff_accepts_every_type(tariff_type: TariffType) -> None:
    """Every documented tariff type should be accepted."""
    tariff = _make_tariff(tariff_type=tariff_type)

    assert tariff.tariff_type is tariff_type


@pytest.mark.parametrize("status", list(TariffStatus))
def test_tariff_accepts_every_status(status: TariffStatus) -> None:
    """Every documented tariff status should be accepted when consistent."""
    overrides: dict[str, Any] = {"status": status}

    if status is TariffStatus.DRAFT:
        overrides.update(
            effective_from=date.today() + timedelta(days=30),
            effective_to=None,
        )
    elif status is TariffStatus.EXPIRED:
        overrides.update(
            effective_from=date.today() - timedelta(days=365),
            effective_to=date.today() - timedelta(days=1),
        )
    elif status is TariffStatus.CANCELLED:
        overrides["effective_to"] = date.today()

    tariff = _make_tariff(**overrides)

    assert tariff.status is status


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (TariffStatus.ACTIVE, True),
        (TariffStatus.DRAFT, False),
        (TariffStatus.EXPIRED, False),
        (TariffStatus.CANCELLED, False),
    ],
)
def test_is_current_reflects_status(
    status: TariffStatus,
    expected: bool,
) -> None:
    """Current status should require ACTIVE and an effective date range."""
    overrides: dict[str, Any] = {"status": status}

    if status is TariffStatus.DRAFT:
        overrides.update(
            effective_from=date.today() + timedelta(days=10),
            effective_to=None,
        )
    elif status is TariffStatus.EXPIRED:
        overrides.update(
            effective_from=date.today() - timedelta(days=20),
            effective_to=date.today() - timedelta(days=1),
        )
    elif status is TariffStatus.CANCELLED:
        overrides["effective_to"] = date.today()

    tariff = _make_tariff(**overrides)

    assert tariff.is_current is expected


def test_duration_days_is_inclusive() -> None:
    """Bounded tariff duration should include both start and end dates."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 31)
    tariff = _make_tariff(
        status=TariffStatus.EXPIRED,
        effective_from=start,
        effective_to=end,
    )

    assert tariff.duration_days == 31


def test_duration_days_is_none_without_end_date() -> None:
    """Open-ended tariffs should not report a bounded duration."""
    tariff = _make_tariff(effective_to=None)

    assert tariff.duration_days is None


def test_calculate_energy_revenue() -> None:
    """Energy revenue should equal exported energy multiplied by rate."""
    tariff = _make_tariff(energy_rate_per_kwh=25.5)

    assert tariff.calculate_energy_revenue(1000.0) == 25500.0


def test_calculate_demand_charge() -> None:
    """Demand charge should equal demand multiplied by demand rate."""
    tariff = _make_tariff(demand_rate_per_kw=2.0)

    assert tariff.calculate_demand_charge(500.0) == 1000.0


def test_calculate_demand_charge_returns_zero_without_rate() -> None:
    """Tariffs without a demand rate should return zero demand charge."""
    tariff = _make_tariff(demand_rate_per_kw=None)

    assert tariff.calculate_demand_charge(500.0) == 0.0


def test_calculate_total_value() -> None:
    """Total tariff value should combine energy revenue and demand charge."""
    tariff = _make_tariff(
        energy_rate_per_kwh=25.5,
        demand_rate_per_kw=2.0,
    )

    assert (
        tariff.calculate_total_value(
            energy_kwh=1000.0,
            demand_kw=500.0,
        )
        == 26500.0
    )


def test_tariff_is_immutable() -> None:
    """Tariff instances should reject field modification."""
    tariff = _make_tariff()

    with pytest.raises(FrozenInstanceError):
        tariff.tariff_name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "tariff_id",
    [
        "",
        "   ",
        "TAR-1",
        "TAR-0001",
        "TAR-000001",
        "TARIFF-00001",
        "TAR-ABCDE",
        "TAR_00001",
    ],
)
def test_tariff_rejects_invalid_tariff_id(tariff_id: str) -> None:
    """Tariff IDs must follow the TAR-00001 format."""
    with pytest.raises(ValueError, match="Invalid tariff_id"):
        _make_tariff(tariff_id=tariff_id)


@pytest.mark.parametrize(
    "plant_id",
    [
        "",
        "   ",
        "PLANT-1",
        "PLANT-01",
        "PLANT-0001",
        "SITE-001",
        "PLANT-ABC",
        "PLANT_001",
    ],
)
def test_tariff_rejects_invalid_plant_id(plant_id: str) -> None:
    """Plant IDs must follow the PLANT-001 format."""
    with pytest.raises(ValueError, match="Invalid plant_id"):
        _make_tariff(plant_id=plant_id)


@pytest.mark.parametrize(
    "currency_code",
    ["", "  ", "US", "USDD", "12A", "U-D", "PK_"],
)
def test_tariff_rejects_invalid_currency_code(currency_code: str) -> None:
    """Currency codes must contain exactly three letters."""
    with pytest.raises(ValueError, match="Invalid currency_code"):
        _make_tariff(currency_code=currency_code)


@pytest.mark.parametrize("tariff_name", ["", "   ", "\t", "\n"])
def test_tariff_rejects_empty_name(tariff_name: str) -> None:
    """Tariff names must contain visible text."""
    with pytest.raises(ValueError, match="tariff_name cannot be empty"):
        _make_tariff(tariff_name=tariff_name)


def test_tariff_rejects_name_longer_than_limit() -> None:
    """Tariff names must not exceed 150 characters."""
    with pytest.raises(ValueError, match="Use no more than 150"):
        _make_tariff(tariff_name="A" * 151)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("contract_reference", ""),
        ("contract_reference", "   "),
        ("notes", ""),
        ("notes", "   "),
    ],
)
def test_tariff_rejects_blank_optional_text(
    field_name: str,
    value: str,
) -> None:
    """Blank optional text should be represented by None."""
    with pytest.raises(ValueError, match=f"{field_name} cannot be empty"):
        _make_tariff(**{field_name: value})


def test_tariff_rejects_long_contract_reference() -> None:
    """Contract references must not exceed 100 characters."""
    with pytest.raises(ValueError, match="Use no more than 100"):
        _make_tariff(contract_reference="A" * 101)


def test_tariff_rejects_long_notes() -> None:
    """Notes must not exceed 1000 characters."""
    with pytest.raises(ValueError, match="Use no more than 1000"):
        _make_tariff(notes="A" * 1001)


@pytest.mark.parametrize(
    ("field_name", "value", "enum_name"),
    [
        ("tariff_type", "fixed", "TariffType"),
        ("tariff_type", 1, "TariffType"),
        ("status", "active", "TariffStatus"),
        ("status", 1, "TariffStatus"),
    ],
)
def test_tariff_rejects_invalid_enums(
    field_name: str,
    value: object,
    enum_name: str,
) -> None:
    """Raw values must not replace tariff enums."""
    with pytest.raises(TypeError, match=f"Use a {enum_name} value"):
        _make_tariff(**{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("effective_from", "2025-01-01"),
        ("effective_from", None),
        ("effective_to", "2025-12-31"),
    ],
)
def test_tariff_rejects_invalid_date_types(
    field_name: str,
    value: object,
) -> None:
    """Effective dates must be date values."""
    with pytest.raises(TypeError, match=f"Invalid {field_name}"):
        _make_tariff(**{field_name: value})


def test_tariff_rejects_end_before_start() -> None:
    """Tariff end date must not precede start date."""
    start = date(2025, 1, 10)
    end = date(2025, 1, 9)

    with pytest.raises(ValueError, match="occurs before effective_from"):
        _make_tariff(
            status=TariffStatus.EXPIRED,
            effective_from=start,
            effective_to=end,
        )


def test_expired_tariff_requires_end_date() -> None:
    """Expired tariffs must include an effective-to date."""
    with pytest.raises(ValueError, match="effective_to is missing"):
        _make_tariff(
            status=TariffStatus.EXPIRED,
            effective_to=None,
        )


def test_active_tariff_rejects_future_start() -> None:
    """Active tariffs must not begin in the future."""
    with pytest.raises(ValueError, match="effective_from.*future"):
        _make_tariff(
            effective_from=date.today() + timedelta(days=1),
            effective_to=None,
        )


def test_active_tariff_rejects_past_end() -> None:
    """Active tariffs must not already be expired."""
    with pytest.raises(ValueError, match="effective_to.*past"):
        _make_tariff(
            effective_from=date.today() - timedelta(days=10),
            effective_to=date.today() - timedelta(days=1),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "energy_rate_per_kwh",
        "demand_rate_per_kw",
        "escalation_rate_pct",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [True, False, "10", [], {}, object()],
)
def test_tariff_rejects_non_numeric_values(
    field_name: str,
    invalid_value: object,
) -> None:
    """Tariff numeric fields must reject non-numeric values."""
    with pytest.raises(TypeError, match=f"Invalid {field_name}"):
        _make_tariff(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "energy_rate_per_kwh",
        "demand_rate_per_kw",
        "escalation_rate_pct",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [math.nan, math.inf, -math.inf],
)
def test_tariff_rejects_non_finite_values(
    field_name: str,
    invalid_value: float,
) -> None:
    """Tariff numeric fields must be finite."""
    with pytest.raises(ValueError, match="must be finite"):
        _make_tariff(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "energy_rate_per_kwh",
        "demand_rate_per_kw",
        "escalation_rate_pct",
    ],
)
def test_tariff_rejects_negative_values(field_name: str) -> None:
    """Tariff numeric fields must not be negative."""
    with pytest.raises(ValueError, match="greater than or equal to zero"):
        _make_tariff(**{field_name: -0.1})


def test_tariff_rejects_escalation_above_100() -> None:
    """Escalation rate must not exceed 100 percent."""
    with pytest.raises(ValueError, match="between 0 and 100"):
        _make_tariff(escalation_rate_pct=100.1)


@pytest.mark.parametrize(
    "method_name",
    [
        "calculate_energy_revenue",
        "calculate_demand_charge",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [True, "10", math.nan, math.inf, -1.0],
)
def test_tariff_calculations_reject_invalid_inputs(
    method_name: str,
    invalid_value: object,
) -> None:
    """Runtime tariff calculations must validate their inputs."""
    tariff = _make_tariff()
    method = getattr(tariff, method_name)

    with pytest.raises((TypeError, ValueError)):
        method(invalid_value)


def test_to_record_returns_complete_serialized_record() -> None:
    """Serialization should return a complete analytics-ready dictionary."""
    start = date.today() - timedelta(days=30)
    end = date.today() + timedelta(days=335)
    tariff = _make_tariff(
        effective_from=start,
        effective_to=end,
    )

    assert tariff.to_record() == {
        "tariff_id": "TAR-00001",
        "plant_id": "PLANT-001",
        "tariff_name": "Solar PPA",
        "tariff_type": "power_purchase_agreement",
        "currency_code": "PKR",
        "energy_rate_per_kwh": 25.5,
        "effective_from": start.isoformat(),
        "effective_to": end.isoformat(),
        "demand_rate_per_kw": 2.0,
        "escalation_rate_pct": 5.0,
        "status": "active",
        "contract_reference": "PPA-001",
        "notes": "Standard utility-scale solar tariff.",
        "is_current": True,
        "duration_days": 366,
    }


def test_to_record_returns_new_dictionary_each_time() -> None:
    """Each serialization call should return an independent dictionary."""
    tariff = _make_tariff()

    first_record = tariff.to_record()
    second_record = tariff.to_record()

    assert first_record == second_record
    assert first_record is not second_record
