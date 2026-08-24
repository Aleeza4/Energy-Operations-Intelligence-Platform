"""Database-backed API data provider and testable provider protocol."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from eoip.anomaly.database_store import anomaly_runs, anomaly_values
from eoip.database.analytics.service import AnalyticsService
from eoip.database.models.alarm import AlarmORM
from eoip.database.models.equipment import EquipmentORM
from eoip.database.models.incident import IncidentORM
from eoip.database.models.plant import PlantORM
from eoip.database.models.scada import SCADAObservationORM
from eoip.database.services.alarm import AlarmService
from eoip.database.services.equipment import EquipmentService
from eoip.database.services.incident import IncidentService
from eoip.database.services.plant import PlantService
from eoip.forecasting.database_store import forecast_runs, forecast_values


class DataProvider(Protocol):
    """Operations required by EOIP HTTP routers."""

    def list_plants(
        self, *, status: str | None, limit: int, offset: int
    ) -> tuple[list[Any], int]: ...

    def get_plant(self, plant_id: str) -> Any | None: ...

    def list_equipment(
        self,
        *,
        plant_id: str | None,
        equipment_type: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]: ...

    def get_equipment(self, equipment_id: str) -> Any | None: ...

    def list_scada(
        self,
        *,
        plant_id: str | None,
        equipment_id: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
        latest: bool = False,
    ) -> tuple[list[Any], int]: ...

    def list_alarms(
        self,
        *,
        plant_id: str | None,
        equipment_id: str | None,
        severity: str | None,
        status: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]: ...

    def get_alarm(self, alarm_id: str) -> Any | None: ...

    def list_incidents(
        self,
        *,
        plant_id: str | None,
        equipment_id: str | None,
        severity: str | None,
        status: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]: ...

    def get_incident(self, incident_id: str) -> Any | None: ...

    def analytics_summary(
        self,
        *,
        plant_id: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> dict[str, Any]: ...

    def list_forecasts(
        self, *, model_name: str | None, horizon: int, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]: ...

    def get_forecast(self, forecast_id: str) -> dict[str, Any] | None: ...

    def list_anomalies(
        self,
        *,
        method: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]: ...

    def get_anomaly(self, anomaly_id: str) -> dict[str, Any] | None: ...

    def anomaly_evaluation(self) -> list[dict[str, Any]]: ...

    def list_recommendations(
        self,
        *,
        plant_id: str | None,
        equipment_id: str | None,
        recommendation_type: str | None,
        minimum_priority: float | None,
        economically_justified: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]: ...

    def get_recommendation(self, recommendation_id: str) -> dict[str, Any] | None: ...


class SQLAlchemyDataProvider:
    """Implement API reads using EOIP SQLAlchemy models and services."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _page(
        self,
        statement: Select[Any],
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]:
        count_statement = select(func.count()).select_from(statement.subquery())
        total = int(self.session.scalar(count_statement) or 0)
        items = list(self.session.scalars(statement.offset(offset).limit(limit)).all())
        return items, total

    def list_plants(
        self, *, status: str | None, limit: int, offset: int
    ) -> tuple[list[PlantORM], int]:
        statement = select(PlantORM).order_by(PlantORM.plant_id)
        if status is not None:
            statement = statement.where(PlantORM.status == status)
        return self._page(statement, limit=limit, offset=offset)

    def get_plant(self, plant_id: str) -> PlantORM | None:
        return PlantService(self.session).get(plant_id)

    def list_equipment(
        self,
        *,
        plant_id: str | None,
        equipment_type: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[EquipmentORM], int]:
        statement = select(EquipmentORM).order_by(EquipmentORM.equipment_id)
        if plant_id is not None:
            statement = statement.where(EquipmentORM.plant_id == plant_id)
        if equipment_type is not None:
            statement = statement.where(EquipmentORM.equipment_type == equipment_type)
        if status is not None:
            statement = statement.where(EquipmentORM.status == status)
        return self._page(statement, limit=limit, offset=offset)

    def get_equipment(self, equipment_id: str) -> EquipmentORM | None:
        return EquipmentService(self.session).get(equipment_id)

    def list_scada(
        self,
        *,
        plant_id: str | None,
        equipment_id: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
        latest: bool = False,
    ) -> tuple[list[SCADAObservationORM], int]:
        statement = select(SCADAObservationORM)
        if plant_id is not None:
            statement = statement.where(SCADAObservationORM.plant_id == plant_id)
        if equipment_id is not None:
            statement = statement.where(
                SCADAObservationORM.equipment_id == equipment_id
            )
        if start_time is not None:
            statement = statement.where(SCADAObservationORM.timestamp >= start_time)
        if end_time is not None:
            statement = statement.where(SCADAObservationORM.timestamp <= end_time)
        statement = statement.order_by(SCADAObservationORM.timestamp.desc())
        if latest:
            limit = min(limit, 100)
        return self._page(statement, limit=limit, offset=offset)

    def list_alarms(
        self,
        *,
        plant_id: str | None,
        equipment_id: str | None,
        severity: str | None,
        status: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AlarmORM], int]:
        statement = select(AlarmORM)
        filters = (
            (AlarmORM.plant_id, plant_id),
            (AlarmORM.equipment_id, equipment_id),
            (AlarmORM.severity, severity),
            (AlarmORM.status, status),
        )
        for column, value in filters:
            if value is not None:
                statement = statement.where(column == value)
        if start_time is not None:
            statement = statement.where(AlarmORM.raised_at >= start_time)
        if end_time is not None:
            statement = statement.where(AlarmORM.raised_at <= end_time)
        statement = statement.order_by(AlarmORM.raised_at.desc())
        return self._page(statement, limit=limit, offset=offset)

    def get_alarm(self, alarm_id: str) -> AlarmORM | None:
        return AlarmService(self.session).get(alarm_id)

    def list_incidents(
        self,
        *,
        plant_id: str | None,
        equipment_id: str | None,
        severity: str | None,
        status: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[IncidentORM], int]:
        statement = select(IncidentORM)
        filters = (
            (IncidentORM.plant_id, plant_id),
            (IncidentORM.equipment_id, equipment_id),
            (IncidentORM.severity, severity),
            (IncidentORM.status, status),
        )
        for column, value in filters:
            if value is not None:
                statement = statement.where(column == value)
        if start_time is not None:
            statement = statement.where(IncidentORM.occurred_at >= start_time)
        if end_time is not None:
            statement = statement.where(IncidentORM.occurred_at <= end_time)
        statement = statement.order_by(IncidentORM.occurred_at.desc())
        return self._page(statement, limit=limit, offset=offset)

    def get_incident(self, incident_id: str) -> IncidentORM | None:
        return IncidentService(self.session).get(incident_id)

    def analytics_summary(
        self,
        *,
        plant_id: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> dict[str, Any]:
        service = AnalyticsService(self.session)
        operations = service.plant_operational_summary()
        if plant_id is not None:
            operations = [row for row in operations if row["plant_id"] == plant_id]
        return {
            "plant_operations": operations,
            "scada_hourly": service.scada_hourly_summary(
                plant_id=plant_id,
                start_at=start_time,
                end_at=end_time,
            )[:1000],
            "open_alarms": [
                row
                for row in service.open_alarm_summary()
                if plant_id is None or row["plant_id"] == plant_id
            ],
            "open_incidents": [
                row
                for row in service.open_incident_summary()
                if plant_id is None or row["plant_id"] == plant_id
            ],
        }

    def list_forecasts(
        self, *, model_name: str | None, horizon: int, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        statement = select(forecast_runs).order_by(forecast_runs.c.generated_at.desc())
        if model_name is not None:
            statement = statement.where(forecast_runs.c.model_name == model_name)
        total = int(
            self.session.scalar(select(func.count()).select_from(statement.subquery()))
            or 0
        )
        rows = self.session.execute(statement.offset(offset).limit(limit)).mappings()
        items = [self._forecast_record(dict(row), horizon=horizon) for row in rows]
        return items, total

    def _forecast_record(
        self, metadata: dict[str, Any], *, horizon: int
    ) -> dict[str, Any]:
        values = self.session.execute(
            select(forecast_values.c.timestamp, forecast_values.c.prediction)
            .where(forecast_values.c.forecast_id == metadata["forecast_id"])
            .order_by(forecast_values.c.timestamp)
            .limit(horizon)
        ).mappings()
        return {**metadata, "units": "target units", "values": list(values)}

    def get_forecast(self, forecast_id: str) -> dict[str, Any] | None:
        row = (
            self.session.execute(
                select(forecast_runs).where(forecast_runs.c.forecast_id == forecast_id)
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else self._forecast_record(dict(row), horizon=1000)

    def list_anomalies(
        self,
        *,
        method: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        statement = (
            select(
                anomaly_runs.c.anomaly_run_id,
                anomaly_runs.c.detector_name,
                anomaly_runs.c.target_column,
                anomaly_runs.c.generated_at,
                anomaly_values.c.timestamp,
                anomaly_values.c.score,
            )
            .join(
                anomaly_values,
                anomaly_values.c.anomaly_run_id == anomaly_runs.c.anomaly_run_id,
            )
            .where(anomaly_values.c.is_anomaly.is_(True))
        )
        if method is not None:
            statement = statement.where(anomaly_runs.c.detector_name == method)
        if start_time is not None:
            statement = statement.where(anomaly_values.c.timestamp >= start_time)
        if end_time is not None:
            statement = statement.where(anomaly_values.c.timestamp <= end_time)
        statement = statement.order_by(anomaly_values.c.timestamp.desc())
        total = int(
            self.session.scalar(select(func.count()).select_from(statement.subquery()))
            or 0
        )
        rows = self.session.execute(statement.offset(offset).limit(limit)).mappings()
        items = [self._anomaly_record(dict(row)) for row in rows]
        return items, total

    @staticmethod
    def _anomaly_record(row: dict[str, Any]) -> dict[str, Any]:
        timestamp = row["timestamp"]
        return {
            **row,
            "anomaly_id": f"{row['anomaly_run_id']}|{timestamp.isoformat()}",
            "status": "detected",
        }

    def get_anomaly(self, anomaly_id: str) -> dict[str, Any] | None:
        items, _ = self.list_anomalies(
            method=None,
            start_time=None,
            end_time=None,
            limit=1000,
            offset=0,
        )
        return next((item for item in items if item["anomaly_id"] == anomaly_id), None)

    def anomaly_evaluation(self) -> list[dict[str, Any]]:
        statement = select(
            anomaly_runs.c.detector_name,
            func.count(anomaly_runs.c.anomaly_run_id).label("run_count"),
            func.sum(anomaly_runs.c.anomaly_count).label("detected_count"),
        ).group_by(anomaly_runs.c.detector_name)
        return [
            {
                **dict(row),
                "note": (
                    "Stored detection volume; labeled precision/recall unavailable."
                ),
            }
            for row in self.session.execute(statement).mappings()
        ]

    def list_recommendations(
        self,
        *,
        plant_id: str | None,
        equipment_id: str | None,
        recommendation_type: str | None,
        minimum_priority: float | None,
        economically_justified: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        del (
            plant_id,
            equipment_id,
            recommendation_type,
            minimum_priority,
            economically_justified,
            limit,
            offset,
        )
        return [], 0

    def get_recommendation(self, recommendation_id: str) -> dict[str, Any] | None:
        del recommendation_id
        return None
