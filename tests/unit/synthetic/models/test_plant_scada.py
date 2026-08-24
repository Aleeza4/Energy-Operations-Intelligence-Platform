"""
Unit tests for the EOIP PlantSCADAObservation domain model.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from eoip.synthetic.models.plant_scada import (
    PlantSCADAObservation,
    PlantSCADAQuality,
)


def _timestamp() -> datetime:
    """Return the standard aligned UTC timestamp."""
    return datetime(2025, 1, 1, 12, 0, tzinfo=UTC)


def _observation(**overrides: object) -> PlantSCADAObservation:
    """Return a valid plant-SCADA observation with optional overrides."""
    data: dict[str, object] = {
        "plant_id": "PLANT-001",
        "meter_id": "MTR-00001",
        "timestamp": _timestamp(),
        "gross_inverter_power_kw": 1_000.0,
        "transformer_loss_kw": 20.0,
        "collection_loss_kw": 10.0,
        "export_power_kw": 970.0,
        "import_power_kw": 0.0,
        "interval_export_energy_kwh": 242.5,
        "interval_import_energy_kwh": 0.0,
        "cumulative_export_energy_kwh": 10_000.0,
        "cumulative_import_energy_kwh": 100.0,
        "grid_available": True,
        "plant_available": True,
        "quality": PlantSCADAQuality.VALID,
    }
    data.update(overrides)
    return PlantSCADAObservation(**data)


def test_valid_construction() -> None:
    """Verify a valid plant-SCADA observation can be created."""
    observation = _observation()

    assert observation.plant_id == "PLANT-001"
    assert observation.meter_id == "MTR-00001"
    assert observation.timestamp == _timestamp()
    assert observation.quality is PlantSCADAQuality.VALID


def test_normalizes_identifiers() -> None:
    """Verify plant and meter identifiers are normalized."""
    observation = _observation(
        plant_id="  plant-001  ",
        meter_id="  mtr-00001  ",
    )

    assert observation.plant_id == "PLANT-001"
    assert observation.meter_id == "MTR-00001"


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("plant_id", "PL-001", "Invalid plant_id"),
        ("meter_id", "METER-00001", "Invalid meter_id"),
    ],
)
def test_rejects_invalid_identifiers(
    field_name: str,
    value: str,
    message: str,
) -> None:
    """Verify malformed identifiers are rejected."""
    with pytest.raises(ValueError, match=message):
        _observation(**{field_name: value})


def test_rejects_non_datetime_timestamp() -> None:
    """Verify timestamp must be a datetime."""
    with pytest.raises(TypeError, match="timestamp must be a datetime"):
        _observation(timestamp="2025-01-01T12:00:00Z")


def test_rejects_timezone_naive_timestamp() -> None:
    """Verify timestamps must be timezone-aware."""
    with pytest.raises(ValueError, match="timezone-aware"):
        _observation(timestamp=datetime(2025, 1, 1, 12, 0))


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2025, 1, 1, 12, 0, 1, tzinfo=UTC),
        datetime(2025, 1, 1, 12, 0, 0, 1, tzinfo=UTC),
    ],
)
def test_rejects_non_zero_seconds_or_microseconds(
    timestamp: datetime,
) -> None:
    """Verify timestamp seconds and microseconds must be zero."""
    with pytest.raises(ValueError, match="seconds and microseconds"):
        _observation(timestamp=timestamp)


@pytest.mark.parametrize(
    "minute",
    [1, 14, 16, 29, 31, 44, 46, 59],
)
def test_rejects_non_aligned_minutes(minute: int) -> None:
    """Verify timestamps align to 15-minute boundaries."""
    with pytest.raises(ValueError, match="15-minute interval"):
        _observation(timestamp=datetime(2025, 1, 1, 12, minute, tzinfo=UTC))


@pytest.mark.parametrize("minute", [0, 15, 30, 45])
def test_accepts_aligned_minutes(minute: int) -> None:
    """Verify all valid quarter-hour boundaries are accepted."""
    observation = _observation(timestamp=datetime(2025, 1, 1, 12, minute, tzinfo=UTC))

    assert observation.timestamp.minute == minute


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("grid_available", 1),
        ("grid_available", "true"),
        ("plant_available", 1),
        ("plant_available", "true"),
    ],
)
def test_rejects_invalid_boolean_fields(
    field_name: str,
    value: object,
) -> None:
    """Verify availability flags must be Boolean."""
    with pytest.raises(TypeError, match=f"{field_name} must be a boolean"):
        _observation(**{field_name: value})


def test_rejects_invalid_quality_type() -> None:
    """Verify quality must use PlantSCADAQuality."""
    with pytest.raises(TypeError, match="PlantSCADAQuality"):
        _observation(quality="valid")


@pytest.mark.parametrize(
    "field_name",
    [
        "gross_inverter_power_kw",
        "transformer_loss_kw",
        "collection_loss_kw",
        "export_power_kw",
        "import_power_kw",
        "interval_export_energy_kwh",
        "interval_import_energy_kwh",
        "cumulative_export_energy_kwh",
        "cumulative_import_energy_kwh",
    ],
)
@pytest.mark.parametrize("value", [True, "1.0", None])
def test_rejects_non_numeric_fields(
    field_name: str,
    value: object,
) -> None:
    """Verify all plant power and energy fields are numeric."""
    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        _observation(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "gross_inverter_power_kw",
        "transformer_loss_kw",
        "collection_loss_kw",
        "export_power_kw",
        "import_power_kw",
        "interval_export_energy_kwh",
        "interval_import_energy_kwh",
        "cumulative_export_energy_kwh",
        "cumulative_import_energy_kwh",
    ],
)
@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_rejects_non_finite_fields(
    field_name: str,
    value: float,
) -> None:
    """Verify all plant power and energy fields are finite."""
    with pytest.raises(ValueError, match=f"{field_name} must be finite"):
        _observation(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "gross_inverter_power_kw",
        "transformer_loss_kw",
        "collection_loss_kw",
        "export_power_kw",
        "import_power_kw",
        "interval_export_energy_kwh",
        "interval_import_energy_kwh",
        "cumulative_export_energy_kwh",
        "cumulative_import_energy_kwh",
    ],
)
def test_rejects_negative_fields(field_name: str) -> None:
    """Verify all plant power and energy fields are non-negative."""
    with pytest.raises(ValueError, match="greater than or equal to zero"):
        _observation(**{field_name: -0.1})


@pytest.mark.parametrize(
    ("export_power_kw", "interval_energy_kwh"),
    [
        (0.0, 0.0),
        (100.0, 25.0),
        (970.0, 242.5),
    ],
)
def test_accepts_valid_export_energy_reconciliation(
    export_power_kw: float,
    interval_energy_kwh: float,
) -> None:
    """Verify export energy equals power multiplied by 0.25 hours."""
    observation = _observation(
        gross_inverter_power_kw=1_000.0,
        transformer_loss_kw=20.0,
        collection_loss_kw=10.0,
        export_power_kw=export_power_kw,
        interval_export_energy_kwh=interval_energy_kwh,
    )

    assert observation.interval_export_energy_kwh == interval_energy_kwh


def test_rejects_invalid_export_energy_reconciliation() -> None:
    """Verify inconsistent export interval energy is rejected."""
    with pytest.raises(
        ValueError,
        match="interval_export_energy_kwh",
    ):
        _observation(interval_export_energy_kwh=240.0)


@pytest.mark.parametrize(
    ("import_power_kw", "interval_energy_kwh"),
    [
        (0.0, 0.0),
        (20.0, 5.0),
        (50.0, 12.5),
    ],
)
def test_accepts_valid_import_energy_reconciliation(
    import_power_kw: float,
    interval_energy_kwh: float,
) -> None:
    """Verify import energy equals power multiplied by 0.25 hours."""
    observation = _observation(
        gross_inverter_power_kw=0.0,
        transformer_loss_kw=0.0,
        collection_loss_kw=0.0,
        export_power_kw=0.0,
        interval_export_energy_kwh=0.0,
        import_power_kw=import_power_kw,
        interval_import_energy_kwh=interval_energy_kwh,
    )

    assert observation.interval_import_energy_kwh == interval_energy_kwh


def test_rejects_invalid_import_energy_reconciliation() -> None:
    """Verify inconsistent import interval energy is rejected."""
    with pytest.raises(
        ValueError,
        match="interval_import_energy_kwh",
    ):
        _observation(
            gross_inverter_power_kw=0.0,
            transformer_loss_kw=0.0,
            collection_loss_kw=0.0,
            export_power_kw=0.0,
            interval_export_energy_kwh=0.0,
            import_power_kw=20.0,
            interval_import_energy_kwh=4.0,
        )


def test_rejects_export_above_power_after_losses() -> None:
    """Verify export cannot exceed gross power after electrical losses."""
    with pytest.raises(
        ValueError,
        match="cannot exceed gross inverter power",
    ):
        _observation(
            gross_inverter_power_kw=1_000.0,
            transformer_loss_kw=20.0,
            collection_loss_kw=10.0,
            export_power_kw=980.0,
            interval_export_energy_kwh=245.0,
        )


def test_accepts_export_equal_to_power_after_losses() -> None:
    """Verify exact post-loss export balance is valid."""
    observation = _observation(
        gross_inverter_power_kw=1_000.0,
        transformer_loss_kw=20.0,
        collection_loss_kw=10.0,
        export_power_kw=970.0,
        interval_export_energy_kwh=242.5,
    )

    assert observation.export_power_kw == 970.0


def test_rejects_simultaneous_export_and_import() -> None:
    """Verify one interval cannot export and import simultaneously."""
    with pytest.raises(
        ValueError,
        match="cannot both be positive",
    ):
        _observation(
            export_power_kw=970.0,
            interval_export_energy_kwh=242.5,
            import_power_kw=10.0,
            interval_import_energy_kwh=2.5,
        )


def test_rejects_export_when_grid_is_unavailable() -> None:
    """Verify grid outages prevent exported power."""
    with pytest.raises(
        ValueError,
        match="Grid-unavailable intervals",
    ):
        _observation(grid_available=False)


def test_accepts_zero_export_when_grid_is_unavailable() -> None:
    """Verify a grid-unavailable interval may contain zero export."""
    observation = _observation(
        gross_inverter_power_kw=0.0,
        transformer_loss_kw=0.0,
        collection_loss_kw=0.0,
        export_power_kw=0.0,
        interval_export_energy_kwh=0.0,
        grid_available=False,
    )

    assert observation.grid_available is False
    assert observation.export_power_kw == 0.0


@pytest.mark.parametrize(
    ("gross_power", "export_power", "interval_energy"),
    [
        (100.0, 0.0, 0.0),
        (100.0, 100.0, 25.0),
    ],
)
def test_rejects_generation_when_plant_is_unavailable(
    gross_power: float,
    export_power: float,
    interval_energy: float,
) -> None:
    """Verify unavailable plants cannot contain generation."""
    with pytest.raises(
        ValueError,
        match="Plant-unavailable intervals",
    ):
        _observation(
            gross_inverter_power_kw=gross_power,
            transformer_loss_kw=0.0,
            collection_loss_kw=0.0,
            export_power_kw=export_power,
            interval_export_energy_kwh=interval_energy,
            plant_available=False,
        )


def test_accepts_zero_generation_when_plant_is_unavailable() -> None:
    """Verify unavailable plants are valid with zero generation."""
    observation = _observation(
        gross_inverter_power_kw=0.0,
        transformer_loss_kw=0.0,
        collection_loss_kw=0.0,
        export_power_kw=0.0,
        interval_export_energy_kwh=0.0,
        plant_available=False,
    )

    assert observation.plant_available is False


def test_missing_quality_requires_zero_interval_measurements() -> None:
    """Verify missing observations cannot expose interval measurements."""
    with pytest.raises(
        ValueError,
        match="Missing-quality observations",
    ):
        _observation(quality=PlantSCADAQuality.MISSING)


def test_missing_quality_accepts_zero_interval_measurements() -> None:
    """Verify missing observations can preserve cumulative registers."""
    observation = _observation(
        gross_inverter_power_kw=0.0,
        transformer_loss_kw=0.0,
        collection_loss_kw=0.0,
        export_power_kw=0.0,
        import_power_kw=0.0,
        interval_export_energy_kwh=0.0,
        interval_import_energy_kwh=0.0,
        quality=PlantSCADAQuality.MISSING,
    )

    assert observation.cumulative_export_energy_kwh == 10_000.0
    assert observation.cumulative_import_energy_kwh == 100.0


def test_total_loss_kw() -> None:
    """Verify combined electrical loss calculation."""
    observation = _observation(
        transformer_loss_kw=20.123456,
        collection_loss_kw=10.123456,
        export_power_kw=969.753088,
        interval_export_energy_kwh=242.438272,
    )

    assert observation.total_loss_kw == 30.246912


def test_delivered_power_before_grid_kw() -> None:
    """Verify post-loss delivered power calculation."""
    observation = _observation(
        gross_inverter_power_kw=1_000.0,
        transformer_loss_kw=20.0,
        collection_loss_kw=10.0,
        export_power_kw=950.0,
        interval_export_energy_kwh=237.5,
    )

    assert observation.delivered_power_before_grid_kw == 970.0


def test_delivered_power_before_grid_is_never_negative() -> None:
    """Verify delivered power is clamped to zero."""
    observation = _observation(
        gross_inverter_power_kw=10.0,
        transformer_loss_kw=8.0,
        collection_loss_kw=5.0,
        export_power_kw=0.0,
        interval_export_energy_kwh=0.0,
    )

    assert observation.delivered_power_before_grid_kw == 0.0


@pytest.mark.parametrize(
    ("export_power", "import_power", "expected"),
    [
        (970.0, 0.0, 970.0),
        (0.0, 20.0, -20.0),
        (0.0, 0.0, 0.0),
    ],
)
def test_net_power_kw(
    export_power: float,
    import_power: float,
    expected: float,
) -> None:
    """Verify signed settlement-boundary power."""
    observation = _observation(
        gross_inverter_power_kw=(1_000.0 if export_power > 0 else 0.0),
        transformer_loss_kw=(20.0 if export_power > 0 else 0.0),
        collection_loss_kw=(10.0 if export_power > 0 else 0.0),
        export_power_kw=export_power,
        interval_export_energy_kwh=export_power * 0.25,
        import_power_kw=import_power,
        interval_import_energy_kwh=import_power * 0.25,
    )

    assert observation.net_power_kw == expected


@pytest.mark.parametrize(
    ("export_power", "expected"),
    [(970.0, True), (0.0, False)],
)
def test_is_exporting(
    export_power: float,
    expected: bool,
) -> None:
    """Verify export-state classification."""
    observation = _observation(
        gross_inverter_power_kw=(1_000.0 if export_power > 0 else 0.0),
        transformer_loss_kw=(20.0 if export_power > 0 else 0.0),
        collection_loss_kw=(10.0 if export_power > 0 else 0.0),
        export_power_kw=export_power,
        interval_export_energy_kwh=export_power * 0.25,
    )

    assert observation.is_exporting is expected


@pytest.mark.parametrize(
    ("import_power", "expected"),
    [(20.0, True), (0.0, False)],
)
def test_is_importing(
    import_power: float,
    expected: bool,
) -> None:
    """Verify import-state classification."""
    observation = _observation(
        gross_inverter_power_kw=0.0,
        transformer_loss_kw=0.0,
        collection_loss_kw=0.0,
        export_power_kw=0.0,
        interval_export_energy_kwh=0.0,
        import_power_kw=import_power,
        interval_import_energy_kwh=import_power * 0.25,
    )

    assert observation.is_importing is expected


def test_to_record_serializes_all_values() -> None:
    """Verify plant-SCADA records are serialization-ready."""
    observation = _observation()

    assert observation.to_record() == {
        "plant_id": "PLANT-001",
        "meter_id": "MTR-00001",
        "timestamp": _timestamp().isoformat(),
        "gross_inverter_power_kw": 1_000.0,
        "transformer_loss_kw": 20.0,
        "collection_loss_kw": 10.0,
        "export_power_kw": 970.0,
        "import_power_kw": 0.0,
        "interval_export_energy_kwh": 242.5,
        "interval_import_energy_kwh": 0.0,
        "cumulative_export_energy_kwh": 10_000.0,
        "cumulative_import_energy_kwh": 100.0,
        "grid_available": True,
        "plant_available": True,
        "quality": PlantSCADAQuality.VALID.value,
        "total_loss_kw": 30.0,
        "delivered_power_before_grid_kw": 970.0,
        "net_power_kw": 970.0,
        "is_exporting": True,
        "is_importing": False,
    }


def test_model_is_immutable() -> None:
    """Verify the frozen dataclass cannot be modified."""
    observation = _observation()

    with pytest.raises(FrozenInstanceError):
        observation.export_power_kw = 0.0  # type: ignore[misc]


def test_slots_prevent_dynamic_attributes() -> None:
    """Verify slots prevent undeclared attributes."""
    observation = _observation()

    with pytest.raises((AttributeError, TypeError)):
        observation.unexpected_field = "value"


def test_quality_enum_values_are_stable() -> None:
    """Verify public quality values remain stable."""
    assert tuple(PlantSCADAQuality) == (
        PlantSCADAQuality.VALID,
        PlantSCADAQuality.ESTIMATED,
        PlantSCADAQuality.MISSING,
    )
