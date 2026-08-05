"""
Tariff reference-data generator for EOIP synthetic data generation.

This module implements the Phase 2 tariff contract from
PHASE_2_IMPLEMENTATION_PLAN.md. It generates complete plant-level effective
date coverage for flat and time-of-use tariffs without writing files or
calculating production revenue KPIs.

The public generator returns a pandas DataFrame with stable columns suitable
for later schema coercion and Parquet publication.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, time
from typing import Any, Protocol

import numpy as np
import pandas as pd


class _RandomContextProtocol(Protocol):
    """Minimal random-context interface required by this generator."""

    def generator(
        self,
        name: str,
        entity_id: str | None = None,
    ) -> np.random.Generator:
        """Return a deterministic NumPy generator for a named stream."""


@dataclass(frozen=True, slots=True)
class TariffWindow:
    """One local-time tariff window within an effective tariff version."""

    window_code: str
    day_category: str
    local_start_time: time | None
    local_end_time: time | None
    rate_multiplier: float

    def __post_init__(self) -> None:
        """Validate the tariff window."""
        normalized_code = self.window_code.strip().upper()
        normalized_day_category = self.day_category.strip().lower()

        object.__setattr__(self, "window_code", normalized_code)
        object.__setattr__(
            self,
            "day_category",
            normalized_day_category,
        )

        if not normalized_code:
            raise ValueError("window_code cannot be empty.")

        if len(normalized_code) > 30:
            raise ValueError("window_code must not exceed 30 characters.")

        if normalized_day_category not in {
            "all_days",
            "weekday",
            "weekend",
        }:
            raise ValueError("day_category must be one of: all_days, weekday, weekend.")

        if isinstance(self.rate_multiplier, bool) or not isinstance(
            self.rate_multiplier,
            (int, float),
        ):
            raise TypeError("rate_multiplier must be numeric.")

        if not math.isfinite(self.rate_multiplier):
            raise ValueError("rate_multiplier must be finite.")

        if self.rate_multiplier <= 0:
            raise ValueError("rate_multiplier must be greater than zero.")

        has_start = self.local_start_time is not None
        has_end = self.local_end_time is not None

        if has_start != has_end:
            raise ValueError(
                "local_start_time and local_end_time must both be set "
                "or both be None."
            )


@dataclass(frozen=True, slots=True)
class TariffGeneratorConfig:
    """Configuration for deterministic plant-level tariff generation."""

    random_seed: int = 20250201
    currency_default: str = "PKR"
    flat_tariff_probability: float = 0.65
    minimum_rate_per_mwh: float = 18_000.0
    maximum_rate_per_mwh: float = 32_000.0
    minimum_escalation_ratio: float = 0.02
    maximum_escalation_ratio: float = 0.08
    contract_name_prefix: str = "EOIP Solar Energy Contract"
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Validate tariff-generator configuration."""
        normalized_currency = self.currency_default.strip().upper()
        normalized_prefix = self.contract_name_prefix.strip()
        normalized_schema_version = self.schema_version.strip()

        object.__setattr__(
            self,
            "currency_default",
            normalized_currency,
        )
        object.__setattr__(
            self,
            "contract_name_prefix",
            normalized_prefix,
        )
        object.__setattr__(
            self,
            "schema_version",
            normalized_schema_version,
        )

        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed,
            int,
        ):
            raise TypeError("random_seed must be an integer.")

        if self.random_seed < 0:
            raise ValueError("random_seed must be non-negative.")

        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise ValueError("currency_default must be a three-letter alphabetic code.")

        if not normalized_prefix:
            raise ValueError("contract_name_prefix cannot be empty.")

        if not normalized_schema_version:
            raise ValueError("schema_version cannot be empty.")

        self._validate_probability(
            field_name="flat_tariff_probability",
            value=self.flat_tariff_probability,
        )

        numeric_fields = (
            "minimum_rate_per_mwh",
            "maximum_rate_per_mwh",
            "minimum_escalation_ratio",
            "maximum_escalation_ratio",
        )

        for field_name in numeric_fields:
            self._validate_finite_number(
                field_name=field_name,
                value=getattr(self, field_name),
            )

        if self.minimum_rate_per_mwh < 0:
            raise ValueError("minimum_rate_per_mwh must be non-negative.")

        if self.maximum_rate_per_mwh < self.minimum_rate_per_mwh:
            raise ValueError(
                "maximum_rate_per_mwh must be greater than or equal to "
                "minimum_rate_per_mwh."
            )

        if not 0.0 <= self.minimum_escalation_ratio <= 1.0:
            raise ValueError("minimum_escalation_ratio must be between 0 and 1.")

        if not 0.0 <= self.maximum_escalation_ratio <= 1.0:
            raise ValueError("maximum_escalation_ratio must be between 0 and 1.")

        if self.maximum_escalation_ratio < self.minimum_escalation_ratio:
            raise ValueError(
                "maximum_escalation_ratio must be greater than or equal to "
                "minimum_escalation_ratio."
            )

    @staticmethod
    def _validate_probability(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a probability between zero and one."""
        TariffGeneratorConfig._validate_finite_number(
            field_name=field_name,
            value=value,
        )

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0 and 1.")

    @staticmethod
    def _validate_finite_number(
        *,
        field_name: str,
        value: float,
    ) -> None:
        """Validate a finite numeric value."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be numeric.")

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be finite.")


_DEFAULT_TOU_WINDOWS: tuple[TariffWindow, ...] = (
    TariffWindow(
        window_code="OFF_PEAK",
        day_category="all_days",
        local_start_time=time(0, 0),
        local_end_time=time(7, 0),
        rate_multiplier=0.82,
    ),
    TariffWindow(
        window_code="SHOULDER_AM",
        day_category="all_days",
        local_start_time=time(7, 0),
        local_end_time=time(17, 0),
        rate_multiplier=1.00,
    ),
    TariffWindow(
        window_code="PEAK",
        day_category="weekday",
        local_start_time=time(17, 0),
        local_end_time=time(22, 0),
        rate_multiplier=1.25,
    ),
    TariffWindow(
        window_code="SHOULDER_PM",
        day_category="all_days",
        local_start_time=time(22, 0),
        local_end_time=time(0, 0),
        rate_multiplier=0.92,
    ),
)


def generate_tariffs(
    plants: pd.DataFrame | Iterable[Any],
    time_range: Any,
    config: TariffGeneratorConfig | None = None,
    random_context: _RandomContextProtocol | None = None,
    *,
    generation_run_id: str = "RUN-UNPUBLISHED",
    tou_windows: Sequence[TariffWindow] = _DEFAULT_TOU_WINDOWS,
) -> pd.DataFrame:
    """
    Generate complete plant-level tariff effective-date coverage.

    Parameters
    ----------
    plants:
        Plant master data as a DataFrame or iterable of objects/mappings.
        Each plant must expose ``plant_id`` and may expose ``currency``.
    time_range:
        Object or mapping exposing ``start`` and ``end``. Start is inclusive
        and end is exclusive.
    config:
        Optional tariff-generator configuration.
    random_context:
        Optional EOIP RandomContext-compatible object.
    generation_run_id:
        Audit identifier included in every output row.
    tou_windows:
        Time-of-use windows used for plants assigned a TOU tariff.

    Returns
    -------
    pandas.DataFrame
        Stable tariff rows ordered by plant, tariff ID, and window code.
    """
    resolved_config = config or TariffGeneratorConfig()
    start_date, end_date = _resolve_effective_dates(time_range)
    plant_records = _normalize_plants(plants)

    if not plant_records:
        raise ValueError("plants must contain at least one plant.")

    if not generation_run_id.strip():
        raise ValueError("generation_run_id cannot be empty.")

    _validate_tou_windows(tou_windows)

    rows: list[dict[str, object]] = []

    for plant_ordinal, plant in enumerate(plant_records, start=1):
        plant_id = plant["plant_id"]
        currency = plant.get("currency") or resolved_config.currency_default
        rng = _plant_rng(
            config=resolved_config,
            random_context=random_context,
            plant_id=plant_id,
        )

        tariff_id = f"TRF-{plant_ordinal:04d}"
        base_rate = round(
            float(
                rng.uniform(
                    resolved_config.minimum_rate_per_mwh,
                    resolved_config.maximum_rate_per_mwh,
                )
            ),
            2,
        )
        escalation_ratio = round(
            float(
                rng.uniform(
                    resolved_config.minimum_escalation_ratio,
                    resolved_config.maximum_escalation_ratio,
                )
            ),
            6,
        )
        contract_name = (
            f"{resolved_config.contract_name_prefix} " f"{plant_ordinal:03d}"
        )

        is_flat = float(rng.random()) < resolved_config.flat_tariff_probability

        if is_flat:
            rows.append(
                _build_row(
                    tariff_id=tariff_id,
                    plant_id=plant_id,
                    tariff_type="flat",
                    contract_name=contract_name,
                    currency=currency,
                    effective_start_date=start_date,
                    effective_end_date=end_date,
                    window_code="FLAT",
                    local_start_time=None,
                    local_end_time=None,
                    day_category="all_days",
                    energy_rate_per_mwh=base_rate,
                    annual_escalation_ratio=escalation_ratio,
                    generation_run_id=generation_run_id,
                    schema_version=resolved_config.schema_version,
                )
            )
            continue

        for window in tou_windows:
            rows.append(
                _build_row(
                    tariff_id=tariff_id,
                    plant_id=plant_id,
                    tariff_type="time_of_use",
                    contract_name=contract_name,
                    currency=currency,
                    effective_start_date=start_date,
                    effective_end_date=end_date,
                    window_code=window.window_code,
                    local_start_time=window.local_start_time,
                    local_end_time=window.local_end_time,
                    day_category=window.day_category,
                    energy_rate_per_mwh=round(
                        base_rate * window.rate_multiplier,
                        2,
                    ),
                    annual_escalation_ratio=escalation_ratio,
                    generation_run_id=generation_run_id,
                    schema_version=resolved_config.schema_version,
                )
            )

    frame = pd.DataFrame.from_records(rows, columns=_output_columns())
    frame = frame.sort_values(
        ["plant_id", "tariff_id", "window_code"],
        kind="stable",
    ).reset_index(drop=True)

    _validate_generated_tariffs(
        frame=frame,
        expected_plant_ids={record["plant_id"] for record in plant_records},
        start_date=start_date,
        end_date=end_date,
    )

    return frame


def _resolve_effective_dates(time_range: Any) -> tuple[date, date]:
    """Resolve inclusive start and exclusive-end coverage dates."""
    start = _extract_value(time_range, "start")
    end = _extract_value(time_range, "end")

    start_timestamp = pd.Timestamp(start)
    end_timestamp = pd.Timestamp(end)

    if start_timestamp.tzinfo is None or end_timestamp.tzinfo is None:
        raise ValueError("time_range start and end must be timezone-aware.")

    if end_timestamp <= start_timestamp:
        raise ValueError("time_range end must be greater than start.")

    start_date = start_timestamp.date()
    exclusive_end_date = end_timestamp.date()

    if end_timestamp.time() != time(0, 0):
        exclusive_end_date += pd.Timedelta(days=1)

    effective_end_date = (
        pd.Timestamp(exclusive_end_date) - pd.Timedelta(days=1)
    ).date()

    return start_date, effective_end_date


def _normalize_plants(
    plants: pd.DataFrame | Iterable[Any],
) -> list[dict[str, str]]:
    """Normalize plant IDs and currencies from supported inputs."""
    if isinstance(plants, pd.DataFrame):
        if "plant_id" not in plants.columns:
            raise ValueError("plants DataFrame must contain plant_id.")

        records = plants.to_dict(orient="records")
    else:
        records = []
        for item in plants:
            if isinstance(item, dict):
                records.append(item)
            else:
                records.append(
                    {
                        "plant_id": getattr(item, "plant_id", None),
                        "currency": getattr(item, "currency", None),
                    }
                )

    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for record in records:
        raw_plant_id = record.get("plant_id")
        if not isinstance(raw_plant_id, str):
            raise TypeError("Each plant_id must be a string.")

        plant_id = raw_plant_id.strip().upper()
        if not plant_id:
            raise ValueError("plant_id cannot be empty.")

        if plant_id in seen_ids:
            raise ValueError(f"Duplicate plant_id '{plant_id}'.")

        seen_ids.add(plant_id)

        raw_currency = record.get("currency")
        currency = (
            raw_currency.strip().upper()
            if isinstance(raw_currency, str) and raw_currency.strip()
            else ""
        )

        if currency and (len(currency) != 3 or not currency.isalpha()):
            raise ValueError(f"Invalid currency '{currency}' for plant {plant_id}.")

        normalized.append(
            {
                "plant_id": plant_id,
                "currency": currency,
            }
        )

    return sorted(normalized, key=lambda item: item["plant_id"])


def _plant_rng(
    *,
    config: TariffGeneratorConfig,
    random_context: _RandomContextProtocol | None,
    plant_id: str,
) -> np.random.Generator:
    """Return the deterministic random stream for one plant tariff."""
    if random_context is not None:
        return random_context.generator("tariffs", entity_id=plant_id)

    plant_entropy = sum(
        (index + 1) * ord(character) for index, character in enumerate(plant_id)
    )
    return np.random.default_rng(config.random_seed + plant_entropy)


def _validate_tou_windows(
    windows: Sequence[TariffWindow],
) -> None:
    """Validate time-of-use window uniqueness and completeness."""
    if not windows:
        raise ValueError("tou_windows must contain at least one window.")

    window_codes = [window.window_code for window in windows]
    if len(window_codes) != len(set(window_codes)):
        raise ValueError("tou_windows contains duplicate window codes.")


def _build_row(
    *,
    tariff_id: str,
    plant_id: str,
    tariff_type: str,
    contract_name: str,
    currency: str,
    effective_start_date: date,
    effective_end_date: date,
    window_code: str,
    local_start_time: time | None,
    local_end_time: time | None,
    day_category: str,
    energy_rate_per_mwh: float,
    annual_escalation_ratio: float,
    generation_run_id: str,
    schema_version: str,
) -> dict[str, object]:
    """Build one canonical tariff row."""
    return {
        "tariff_id": tariff_id,
        "plant_id": plant_id,
        "tariff_type": tariff_type,
        "contract_name": contract_name,
        "currency": currency,
        "effective_start_date": effective_start_date,
        "effective_end_date": effective_end_date,
        "window_code": window_code,
        "local_start_time": (
            local_start_time.isoformat() if local_start_time is not None else None
        ),
        "local_end_time": (
            local_end_time.isoformat() if local_end_time is not None else None
        ),
        "day_category": day_category,
        "energy_rate_per_mwh": energy_rate_per_mwh,
        "annual_escalation_ratio": annual_escalation_ratio,
        "generation_run_id": generation_run_id.strip(),
        "schema_version": schema_version,
    }


def _validate_generated_tariffs(
    *,
    frame: pd.DataFrame,
    expected_plant_ids: set[str],
    start_date: date,
    end_date: date,
) -> None:
    """Validate mandatory tariff invariants before returning."""
    if frame.empty:
        raise ValueError("Generated tariff frame is empty.")

    if frame[list(_primary_key_columns())].duplicated().any():
        raise ValueError(
            "Generated tariffs contain duplicate " "(tariff_id, window_code) keys."
        )

    actual_plant_ids = set(frame["plant_id"].astype(str))
    if actual_plant_ids != expected_plant_ids:
        raise ValueError("Generated tariff plant coverage does not match input plants.")

    if (frame["energy_rate_per_mwh"] < 0).any():
        raise ValueError("Generated tariff rates must be non-negative.")

    if (
        frame["effective_start_date"].ne(start_date).any()
        or frame["effective_end_date"].ne(end_date).any()
    ):
        raise ValueError("Generated tariff effective-date coverage is inconsistent.")

    flat_rows = frame["tariff_type"].eq("flat")
    if frame.loc[flat_rows, "local_start_time"].notna().any():
        raise ValueError("Flat tariffs must not define local time windows.")

    if frame.loc[flat_rows, "local_end_time"].notna().any():
        raise ValueError("Flat tariffs must not define local time windows.")


def _extract_value(source: Any, name: str) -> Any:
    """Extract a named value from a mapping or object."""
    if isinstance(source, dict):
        if name not in source:
            raise ValueError(f"time_range is missing '{name}'.")
        return source[name]

    if not hasattr(source, name):
        raise ValueError(f"time_range is missing '{name}'.")

    return getattr(source, name)


def _primary_key_columns() -> tuple[str, str]:
    """Return the canonical tariff primary-key columns."""
    return ("tariff_id", "window_code")


def _output_columns() -> tuple[str, ...]:
    """Return stable tariff output column order."""
    return (
        "tariff_id",
        "plant_id",
        "tariff_type",
        "contract_name",
        "currency",
        "effective_start_date",
        "effective_end_date",
        "window_code",
        "local_start_time",
        "local_end_time",
        "day_category",
        "energy_rate_per_mwh",
        "annual_escalation_ratio",
        "generation_run_id",
        "schema_version",
    )
