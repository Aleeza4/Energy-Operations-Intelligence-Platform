"""Typed public response and query schemas for the EOIP API."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from eoip.api.errors import APIError

Identifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
    ),
]


class APIModel(BaseModel):
    """Base response schema supporting ORM attribute conversion."""

    model_config = ConfigDict(from_attributes=True)


class Page[ItemT](APIModel):
    """Consistent paginated collection envelope."""

    items: list[ItemT]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=1000)
    offset: int = Field(ge=0)


class TimeRangeParams(BaseModel):
    """Optional inclusive API time range."""

    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_order(self) -> TimeRangeParams:
        """Reject reversed time ranges."""
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            raise ValueError("start_time must not be after end_time")
        return self


def get_time_range(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
) -> TimeRangeParams:
    """Build a validated time range without leaking dependency validation errors."""
    if start_time is not None and end_time is not None and start_time > end_time:
        raise APIError(
            status_code=422,
            code="invalid_time_range",
            message="start_time must not be after end_time.",
        )
    return TimeRangeParams(start_time=start_time, end_time=end_time)


TimeRange = Annotated[TimeRangeParams, Depends(get_time_range)]


class HealthResponse(APIModel):
    status: str
    service: str
    version: str
    environment: str


class ReadinessResponse(HealthResponse):
    dependencies: dict[str, str]


class PlantResponse(APIModel):
    plant_id: str
    plant_name: str
    region: str
    latitude: float
    longitude: float
    dc_capacity_mw: float
    ac_capacity_mw: float
    commissioning_date: date
    status: str
    timezone_name: str


class EquipmentResponse(APIModel):
    equipment_id: str
    plant_id: str
    equipment_name: str
    equipment_type: str
    manufacturer: str
    model_number: str
    serial_number: str
    commissioning_date: date
    rated_power_kw: float | None
    parent_equipment_id: str | None
    status: str


class SCADAResponse(APIModel):
    plant_id: str
    equipment_id: str
    timestamp: datetime
    active_power_kw: float
    interval_energy_kwh: float
    dc_voltage_v: float
    dc_current_a: float
    ac_voltage_v: float
    ac_current_a: float
    frequency_hz: float
    power_factor: float
    equipment_available: bool
    grid_available: bool
    operating_state: str
    quality: str


class AlarmResponse(APIModel):
    alarm_id: str
    plant_id: str
    equipment_id: str
    alarm_code: str
    alarm_name: str
    category: str
    severity: str
    raised_at: datetime
    status: str
    acknowledged_at: datetime | None
    cleared_at: datetime | None
    message: str | None


class IncidentResponse(APIModel):
    incident_id: str
    plant_id: str
    equipment_id: str
    incident_name: str
    category: str
    severity: str
    occurred_at: datetime
    status: str
    detected_at: datetime | None
    resolved_at: datetime | None
    description: str | None
    root_cause: str | None
    linked_alarm_id: str | None


class AnalyticsSummaryResponse(APIModel):
    plant_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    units: dict[str, str]
    plant_operations: list[dict[str, Any]]
    scada_hourly: list[dict[str, Any]]
    open_alarms: list[dict[str, Any]]
    open_incidents: list[dict[str, Any]]


class ForecastPoint(APIModel):
    timestamp: datetime
    prediction: float


class ForecastResponse(APIModel):
    forecast_id: str
    model_name: str
    target_column: str
    generated_at: datetime
    row_count: int
    units: str
    values: list[ForecastPoint] = Field(default_factory=list)


class AnomalyResponse(APIModel):
    anomaly_id: str
    anomaly_run_id: str
    timestamp: datetime
    score: float | None
    detector_name: str
    target_column: str
    generated_at: datetime
    severity: str | None = None
    status: str = "detected"


class AnomalyEvaluationResponse(APIModel):
    detector_name: str
    run_count: int
    detected_count: int
    note: str


class RecommendationType(StrEnum):
    MAINTENANCE = "maintenance"
    PERFORMANCE_RECOVERY = "performance_recovery"
    MONITOR = "monitor"
    NO_ACTION = "no_action"


class RecommendationResponse(APIModel):
    recommendation_id: str
    plant_id: str | None = None
    equipment_id: str
    recommendation_type: RecommendationType
    action: str
    rationale: str
    priority_rank: int | None = None
    priority_score: float | None = Field(default=None, ge=0, le=1)
    risk_score: float | None = Field(default=None, ge=0, le=1)
    recoverable_energy_kwh: float | None = Field(default=None, ge=0)
    expected_benefit: float = Field(ge=0)
    net_financial_impact: float | None = None
    roi_percent: float | None = None
    economically_justified: bool | None = None


class Role(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class UserResponse(APIModel):
    username: str
    role: Role


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(gt=0)


class AdminStatusResponse(APIModel):
    service: str
    environment: str
    authenticated_user: str
    role: Role
    database_configured: bool
