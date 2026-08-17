"""Core KPI abstractions for the EOIP analytics engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class KPIStatus(StrEnum):
    """Status of a KPI calculation result."""

    VALID = "valid"
    INSUFFICIENT_DATA = "insufficient_data"
    INVALID_INPUT = "invalid_input"


@dataclass(frozen=True, slots=True)
class KPIWindow:
    """Inclusive-exclusive time window used for KPI calculation."""

    start_at: datetime
    end_at: datetime

    def __post_init__(self) -> None:
        """Validate KPI window boundaries."""
        if self.start_at.tzinfo is None:
            raise ValueError("start_at must be timezone-aware")

        if self.end_at.tzinfo is None:
            raise ValueError("end_at must be timezone-aware")

        if self.end_at <= self.start_at:
            raise ValueError("end_at must be later than start_at")

    @property
    def duration_seconds(self) -> float:
        """Return total window duration in seconds."""
        return (self.end_at - self.start_at).total_seconds()

    @property
    def duration_hours(self) -> float:
        """Return total window duration in hours."""
        return self.duration_seconds / 3600.0


@dataclass(frozen=True, slots=True)
class KPIResult:
    """Standard result returned by EOIP KPI calculations."""

    name: str
    value: float | None
    unit: str
    status: KPIStatus
    window: KPIWindow
    sample_count: int = 0
    message: str | None = None

    def __post_init__(self) -> None:
        """Validate KPI result fields."""
        if not self.name.strip():
            raise ValueError("name must not be empty")

        if not self.unit.strip():
            raise ValueError("unit must not be empty")

        if self.sample_count < 0:
            raise ValueError("sample_count must not be negative")

        if self.status is KPIStatus.VALID and self.value is None:
            raise ValueError("value must be provided when KPI status is valid")

        if self.status is not KPIStatus.VALID and self.value is not None:
            raise ValueError("value must be None when KPI status is not valid")


class KPICalculator(Protocol):
    """Protocol implemented by EOIP KPI calculators."""

    @property
    def name(self) -> str:
        """Return KPI name."""
        ...

    @property
    def unit(self) -> str:
        """Return KPI unit."""
        ...

    def calculate(
        self,
        *,
        window: KPIWindow,
    ) -> KPIResult:
        """Calculate the KPI for a time window."""
        ...


def valid_result(
    *,
    name: str,
    value: float,
    unit: str,
    window: KPIWindow,
    sample_count: int,
) -> KPIResult:
    """Create a valid KPI result."""
    return KPIResult(
        name=name,
        value=value,
        unit=unit,
        status=KPIStatus.VALID,
        window=window,
        sample_count=sample_count,
    )


def insufficient_data_result(
    *,
    name: str,
    unit: str,
    window: KPIWindow,
    sample_count: int = 0,
    message: str = "Insufficient data for KPI calculation.",
) -> KPIResult:
    """Create an insufficient-data KPI result."""
    return KPIResult(
        name=name,
        value=None,
        unit=unit,
        status=KPIStatus.INSUFFICIENT_DATA,
        window=window,
        sample_count=sample_count,
        message=message,
    )


def invalid_input_result(
    *,
    name: str,
    unit: str,
    window: KPIWindow,
    message: str,
) -> KPIResult:
    """Create an invalid-input KPI result."""
    return KPIResult(
        name=name,
        value=None,
        unit=unit,
        status=KPIStatus.INVALID_INPUT,
        window=window,
        message=message,
    )
