"""
SQLAlchemy ORM model for EOIP weather observations.

This model mirrors the authoritative synthetic WeatherObservation domain model
while adding relational persistence, database constraints, indexes, audit
timestamps, and conversion helpers for PostgreSQL and TimescaleDB.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eoip.database.base import Base
from eoip.database.models.plant import PlantORM
from eoip.synthetic.models.weather import WeatherObservation, WeatherQuality


class WeatherObservationORM(Base):
    """PostgreSQL-backed weather observation for one plant station."""

    __tablename__ = "weather_observations"

    __table_args__ = (
        CheckConstraint(
            "ghi_wm2 >= 0 AND ghi_wm2 <= 1500",
            name="ghi_range",
        ),
        CheckConstraint(
            "dni_wm2 >= 0 AND dni_wm2 <= 1500",
            name="dni_range",
        ),
        CheckConstraint(
            "dhi_wm2 >= 0 AND dhi_wm2 <= 1500",
            name="dhi_range",
        ),
        CheckConstraint(
            "ambient_temperature_c >= -40 " "AND ambient_temperature_c <= 70",
            name="ambient_temperature_range",
        ),
        CheckConstraint(
            "module_temperature_c >= -40 " "AND module_temperature_c <= 120",
            name="module_temperature_range",
        ),
        CheckConstraint(
            "wind_speed_ms >= 0 AND wind_speed_ms <= 70",
            name="wind_speed_range",
        ),
        CheckConstraint(
            "relative_humidity_pct >= 0 " "AND relative_humidity_pct <= 100",
            name="relative_humidity_range",
        ),
        CheckConstraint(
            "quality IN ('valid', 'estimated', 'missing')",
            name="valid_quality",
        ),
        Index("ix_weather_observations_plant_id", "plant_id"),
        Index("ix_weather_observations_timestamp", "timestamp"),
        Index(
            "ix_weather_observations_plant_timestamp",
            "plant_id",
            "timestamp",
        ),
        Index(
            "ix_weather_observations_station_timestamp",
            "weather_station_id",
            "timestamp",
        ),
        Index(
            "ix_weather_observations_quality_timestamp",
            "quality",
            "timestamp",
        ),
    )

    plant_id: Mapped[str] = mapped_column(
        String(9),
        ForeignKey(
            "plants.plant_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    weather_station_id: Mapped[str] = mapped_column(
        String(6),
        primary_key=True,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    ghi_wm2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    dni_wm2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    dhi_wm2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    ambient_temperature_c: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    module_temperature_c: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    wind_speed_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    relative_humidity_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    quality: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WeatherQuality.VALID.value,
        server_default=WeatherQuality.VALID.value,
    )
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    plant: Mapped[PlantORM] = relationship(
        PlantORM,
        lazy="selectin",
    )

    @property
    def total_horizontal_irradiance(self) -> float:
        """Return combined global and diffuse horizontal irradiance."""
        return round(self.ghi_wm2 + self.dhi_wm2, 4)

    @property
    def is_daylight(self) -> bool:
        """Return whether the observation represents daylight conditions."""
        return self.ghi_wm2 > 0

    def to_domain(self) -> WeatherObservation:
        """Convert this ORM record to the authoritative domain model."""
        return WeatherObservation(
            plant_id=self.plant_id,
            weather_station_id=self.weather_station_id,
            timestamp=self.timestamp,
            ghi_wm2=self.ghi_wm2,
            dni_wm2=self.dni_wm2,
            dhi_wm2=self.dhi_wm2,
            ambient_temperature_c=self.ambient_temperature_c,
            module_temperature_c=self.module_temperature_c,
            wind_speed_ms=self.wind_speed_ms,
            relative_humidity_pct=self.relative_humidity_pct,
            quality=WeatherQuality(self.quality),
        )

    @classmethod
    def from_domain(
        cls,
        observation: WeatherObservation,
    ) -> WeatherObservationORM:
        """Create an ORM record from a weather domain observation."""
        if not isinstance(observation, WeatherObservation):
            raise TypeError("observation must be a WeatherObservation instance.")

        return cls(
            plant_id=observation.plant_id,
            weather_station_id=observation.weather_station_id,
            timestamp=observation.timestamp,
            ghi_wm2=observation.ghi_wm2,
            dni_wm2=observation.dni_wm2,
            dhi_wm2=observation.dhi_wm2,
            ambient_temperature_c=observation.ambient_temperature_c,
            module_temperature_c=observation.module_temperature_c,
            wind_speed_ms=observation.wind_speed_ms,
            relative_humidity_pct=observation.relative_humidity_pct,
            quality=observation.quality.value,
        )

    def update_from_domain(
        self,
        observation: WeatherObservation,
    ) -> None:
        """Update mutable fields from a matching weather observation."""
        if not isinstance(observation, WeatherObservation):
            raise TypeError("observation must be a WeatherObservation instance.")

        if (
            observation.weather_station_id != self.weather_station_id
            or observation.timestamp != self.timestamp
        ):
            raise ValueError(
                "Cannot update WeatherObservationORM with a different "
                "weather_station_id or timestamp."
            )

        self.plant_id = observation.plant_id
        self.ghi_wm2 = observation.ghi_wm2
        self.dni_wm2 = observation.dni_wm2
        self.dhi_wm2 = observation.dhi_wm2
        self.ambient_temperature_c = observation.ambient_temperature_c
        self.module_temperature_c = observation.module_temperature_c
        self.wind_speed_ms = observation.wind_speed_ms
        self.relative_humidity_pct = observation.relative_humidity_pct
        self.quality = observation.quality.value

    def to_record(self) -> dict[str, object]:
        """Return a serialization-ready database record."""
        return {
            "plant_id": self.plant_id,
            "weather_station_id": self.weather_station_id,
            "timestamp": self.timestamp.isoformat(),
            "ghi_wm2": self.ghi_wm2,
            "dni_wm2": self.dni_wm2,
            "dhi_wm2": self.dhi_wm2,
            "ambient_temperature_c": self.ambient_temperature_c,
            "module_temperature_c": self.module_temperature_c,
            "wind_speed_ms": self.wind_speed_ms,
            "relative_humidity_pct": self.relative_humidity_pct,
            "quality": self.quality,
            "total_horizontal_irradiance": (self.total_horizontal_irradiance),
            "is_daylight": self.is_daylight,
            "inserted_at": (
                self.inserted_at.isoformat() if self.inserted_at is not None else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
        }

    def __repr__(self) -> str:
        """Return a concise developer representation."""
        return (
            "WeatherObservationORM("
            f"weather_station_id={self.weather_station_id!r}, "
            f"timestamp={self.timestamp!r}, "
            f"quality={self.quality!r}"
            ")"
        )


__all__ = ["WeatherObservationORM"]
