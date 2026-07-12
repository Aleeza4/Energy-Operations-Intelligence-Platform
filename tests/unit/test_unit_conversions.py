import pytest

from src.features.unit_conversions import UnitConverter


def test_kw_to_mw() -> None:
    assert UnitConverter.kw_to_mw(1000) == 1


def test_mw_to_kw() -> None:
    assert UnitConverter.mw_to_kw(2.5) == 2500


def test_kwh_to_mwh() -> None:
    assert UnitConverter.kwh_to_mwh(1500) == 1.5


def test_mwh_to_kwh() -> None:
    assert UnitConverter.mwh_to_kwh(3) == 3000


def test_minutes_to_hours() -> None:
    assert UnitConverter.minutes_to_hours(90) == 1.5


def test_hours_to_minutes() -> None:
    assert UnitConverter.hours_to_minutes(2) == 120


def test_power_to_energy_for_15_minute_interval() -> None:
    result = UnitConverter.power_to_energy(
        average_power_kw=400,
        interval_minutes=15,
    )

    assert result == 100


def test_dc_ac_ratio() -> None:
    assert (
        UnitConverter.dc_ac_ratio(
            dc_capacity_mwp=25,
            ac_capacity_mw=20,
        )
        == 1.25
    )


def test_dc_ac_ratio_rejects_zero_ac_capacity() -> None:
    with pytest.raises(
        ValueError,
        match="AC capacity must be greater than zero.",
    ):
        UnitConverter.dc_ac_ratio(
            dc_capacity_mwp=25,
            ac_capacity_mw=0,
        )
