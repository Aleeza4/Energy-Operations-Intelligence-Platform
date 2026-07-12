"""
Unit conversion utilities for the
Energy Operations Intelligence Platform.

All conversions follow the canonical
measurement conventions defined in:

configs/units.yaml
"""

from __future__ import annotations


class UnitConverter:
    """Utility class for engineering unit conversions."""

    # -------------------------
    # Power
    # -------------------------

    @staticmethod
    def kw_to_mw(value: float) -> float:
        return value / 1000

    @staticmethod
    def mw_to_kw(value: float) -> float:
        return value * 1000

    # -------------------------
    # Energy
    # -------------------------

    @staticmethod
    def kwh_to_mwh(value: float) -> float:
        return value / 1000

    @staticmethod
    def mwh_to_kwh(value: float) -> float:
        return value * 1000

    # -------------------------
    # Duration
    # -------------------------

    @staticmethod
    def minutes_to_hours(minutes: float) -> float:
        return minutes / 60

    @staticmethod
    def hours_to_minutes(hours: float) -> float:
        return hours * 60

    # -------------------------
    # Power → Energy
    # -------------------------

    @staticmethod
    def power_to_energy(
        average_power_kw: float,
        interval_minutes: float,
    ) -> float:
        """
        Convert average power over an interval
        into interval energy.

        Example:
        400 kW for 15 minutes

        =100 kWh
        """

        hours = interval_minutes / 60

        return average_power_kw * hours

    # -------------------------
    # DC / AC Ratio
    # -------------------------

    @staticmethod
    def dc_ac_ratio(
        dc_capacity_mwp: float,
        ac_capacity_mw: float,
    ) -> float:

        if ac_capacity_mw <= 0:
            raise ValueError("AC capacity must be greater than zero.")

        return dc_capacity_mwp / ac_capacity_mw
